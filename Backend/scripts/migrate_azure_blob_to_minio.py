#!/usr/bin/env python3
"""
One-time copy of all objects from Azure Blob Storage to MinIO.

Preserves object keys (paths) so the app finds files at the same paths.

Prerequisites:
  pip install azure-storage-blob minio python-dotenv

Usage (from Backend/, MinIO running, bucket created):

  python scripts/migrate_azure_blob_to_minio.py
  python scripts/migrate_azure_blob_to_minio.py --dry-run
  python scripts/migrate_azure_blob_to_minio.py --prefix graphragoutput/
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = str(v).strip().strip('"').strip("'")
    return v or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy Azure Blob container to MinIO bucket")
    parser.add_argument("--dry-run", action="store_true", help="List objects only, no upload")
    parser.add_argument("--prefix", default="", help="Only copy blobs under this prefix")
    parser.add_argument(
        "--azure-connection",
        default=None,
        help="Azure connection string (default: AZURE_STORAGE_CONNECTION_STRING from unified.env)",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / "unified.env")
    except ImportError:
        pass

    azure_conn = args.azure_connection or _clean(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    if not azure_conn:
        print(
            "ERROR: Set AZURE_STORAGE_CONNECTION_STRING in unified.env "
            "(or pass --azure-connection) for the source Azure account."
        )
        return 2

    container = _clean(os.getenv("BLOB_STORAGE_CONTAINER_NAME")) or "unifiedproddocs"
    prefix = (args.prefix or "").lstrip("/")

    from azure.storage.blob import BlobServiceClient as AzureBlobClient

    from utility.minio_blob_store import _minio_client, to_minio_object_key

    azure_client = AzureBlobClient.from_connection_string(azure_conn)
    azure_container = azure_client.get_container_client(container)
    minio = _minio_client()

    if not minio.bucket_exists(container):
        if args.dry_run:
            print(f"[dry-run] would create bucket: {container}")
        else:
            minio.make_bucket(container)
            print(f"Created MinIO bucket: {container}")

    copied = 0
    skipped = 0
    errors = 0

    for blob in azure_container.list_blobs(name_starts_with=prefix or None):
        name = blob.name
        if args.dry_run:
            print(f"  would copy: {name}")
            copied += 1
            continue
        try:
            minio_key = to_minio_object_key(name)
            try:
                minio.stat_object(container, minio_key)
                skipped += 1
                continue
            except Exception:
                pass

            downloader = azure_container.get_blob_client(name).download_blob()
            data = downloader.readall()
            from io import BytesIO

            minio.put_object(
                container,
                minio_key,
                BytesIO(data),
                length=len(data),
            )
            copied += 1
            if copied % 50 == 0:
                print(f"  copied {copied} objects...")
        except Exception as exc:
            errors += 1
            print(f"  ERROR {name}: {exc}")

    print(
        f"Done. copied={copied} skipped_existing={skipped} errors={errors} "
        f"bucket={container} prefix={prefix or '(all)'}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
