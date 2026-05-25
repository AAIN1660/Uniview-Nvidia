#!/usr/bin/env python3
"""
Verify GraphRAG stored embeddings (blob parquets) match active NVIDIA/Azure config.

Usage (from Backend, with unified.env loaded or present on disk):

  python graphrag_verify_embeddings.py
  python graphrag_verify_embeddings.py --category b7ec5651-e2b5-4343-8f83-e691d012104c
  python graphrag_verify_embeddings.py --folder graphragoutput/<uuid>/artifacts
  python graphrag_verify_embeddings.py --local-dir .\\data\\output\\artifacts
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GraphRAG artifact embedding dimensions")
    parser.add_argument(
        "--category",
        help="Category UUID (uses graphragoutput/<id>/artifacts)",
    )
    parser.add_argument(
        "--folder",
        help="Full blob prefix, e.g. graphragoutput/<uuid>/artifacts",
    )
    parser.add_argument(
        "--local-dir",
        help="Read create_final_entities.parquet from a local directory instead of blob",
    )
    parser.add_argument(
        "--no-query-probe",
        action="store_true",
        help="Skip live NIM/Azure query embedding dimension probe",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / "unified.env")
    except ImportError:
        pass

    from utility.graphrag_index_env import ensure_graphrag_index_env

    ensure_graphrag_index_env()

    from utility.graphrag_artifacts import resolve_graph_artifacts_folder
    from utility.graphrag_embedding_inspect import format_report, verify_graphrag_artifacts

    import os

    if args.folder:
        folder = args.folder.strip().rstrip("/")
    else:
        folder = resolve_graph_artifacts_folder(args.category)

    blob_client = None
    container = os.getenv("BLOB_STORAGE_CONTAINER_NAME")
    if not args.local_dir:
        if not container:
            print("ERROR: set BLOB_STORAGE_CONTAINER_NAME or use --local-dir")
            return 2
        from utility.blob_storage import get_blob_service_client

        blob_client = get_blob_service_client()

    report = verify_graphrag_artifacts(
        folder_path=folder,
        container_name=container,
        blob_service_client=blob_client,
        local_artifacts_dir=args.local_dir,
        probe_query_embed=not args.no_query_probe,
    )
    print(format_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
