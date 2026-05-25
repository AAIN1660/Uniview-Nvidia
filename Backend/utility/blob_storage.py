# -*- coding: utf-8 -*-
"""
Object storage: MinIO only (Azure Blob removed).
===============================================

    from utility.blob_storage import get_blob_service_client, BlobServiceClient

Blob I/O uses MINIO_* from unified.env. Azure Storage connection strings are
not used for objects (queues still use AZURE_STORAGE_CONNECTION_STRING).
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / "unified.env")
except ImportError:
    pass

from utility.minio_blob_store import (  # noqa: F401
    BlobServiceClient,
    PublicAccess,
    ResourceExistsError,
    sync_directory_to_bucket,
)


def get_blob_service_client() -> BlobServiceClient:
    """Return the process-wide MinIO-backed blob client."""
    return BlobServiceClient.from_connection_string(None)


# Log once on import.
_endpoint = (os.getenv("MINIO_ENDPOINT") or "").strip()
_bucket = (os.getenv("BLOB_STORAGE_CONTAINER_NAME") or "").strip()
print(f"[blob-storage] backend=minio endpoint={_endpoint} bucket={_bucket}")
