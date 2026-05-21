#!/usr/bin/env python3
"""
Run GraphRAG indexing with NVIDIA NIM corpus embedding extras (passage ``input_type``).

Usage (from Backend cwd): python graphrag_index_runner.py --root <graphrag-project-dir>

Replaces ``python -m graphrag.index`` for this repo so asymmetric NIM embeddings work during
indexing. Query-time embeddings are configured in ``utility/inference.py`` via
``utility.graphrag_text_embedder``.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / "unified.env")
    except ImportError:
        pass

    # Default aligns with NVIDIA E5-style dual encoders (corpus vs query).
    os.environ.setdefault("GRAPHRAG_INDEX_EMBEDDING_INPUT_TYPE", "passage")

    from utility.graphrag_index_env import ensure_graphrag_index_env

    ensure_graphrag_index_env()

    from utility.graphrag_nim_index_embedding_patch import (
        apply_graphrag_index_nim_embedding_passage_patch,
    )

    apply_graphrag_index_nim_embedding_passage_patch()

    runpy.run_module("graphrag.index.__main__", run_name="__main__")


if __name__ == "__main__":
    main()
