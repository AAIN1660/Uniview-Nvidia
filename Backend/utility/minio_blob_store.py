# -*- coding: utf-8 -*-
"""
MinIO (S3-compatible) adapter for Azure Blob Storage.

MinIO implementation for object storage (replaces Azure Blob in this codebase).

Callers keep using BlobServiceClient.from_connection_string(...),
get_container_client, get_blob_client, upload_blob, download_blob,
list_blobs, and delete_blob unchanged.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import BinaryIO, Iterator

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "minio package is required. Install with: pip install minio"
    ) from exc


class ResourceExistsError(Exception):
    """Raised when create_container is called for an existing bucket."""


class PublicAccess:
    """Stub for azure.storage.blob.PublicAccess (unused on MinIO path)."""
    CONTAINER = "container"


def _clean_env(v: str | None) -> str | None:
    if v is None:
        return None
    v = str(v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v


def to_minio_object_key(logical_name: str) -> str:
    """Encode logical blob path for S3/MinIO (colons are invalid in object keys)."""
    return logical_name.lstrip("/").replace(":", "%3A")


def from_minio_object_key(stored_name: str) -> str:
    """Decode object key from MinIO back to the logical path the app expects."""
    return stored_name.replace("%3A", ":")


def get_blob_service_client() -> "BlobServiceClient":
    return BlobServiceClient.from_connection_string(None)


def _minio_client() -> Minio:
    endpoint = _clean_env(os.getenv("MINIO_ENDPOINT"))
    access_key = _clean_env(os.getenv("MINIO_ACCESS_KEY"))
    secret_key = _clean_env(os.getenv("MINIO_SECRET_KEY"))
    secure_raw = (_clean_env(os.getenv("MINIO_SECURE")) or "false").lower()
    if not endpoint or not access_key or not secret_key:
        raise ValueError(
            "MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY must be set "
            "for MinIO object storage"
        )
    secure = secure_raw in ("1", "true", "yes")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


@dataclass
class _BlobProperties:
    name: str


class _DownloadStream:
    def __init__(self, data: bytes):
        self._data = data

    def readall(self) -> bytes:
        return self._data


class _BlobClient:
    def __init__(self, client: Minio, bucket: str, object_name: str):
        self._client = client
        self._bucket = bucket
        self._logical_name = object_name.lstrip("/")
        self._object_name = to_minio_object_key(self._logical_name)

    def upload_blob(self, data: BinaryIO | bytes, overwrite: bool = True) -> None:
        if isinstance(data, bytes):
            payload = io.BytesIO(data)
            length = len(data)
        else:
            payload = data
            payload.seek(0, os.SEEK_END)
            length = payload.tell()
            payload.seek(0)
        self._client.put_object(
            self._bucket,
            self._object_name,
            payload,
            length=length,
        )

    def download_blob(self) -> _DownloadStream:
        response = self._client.get_object(self._bucket, self._object_name)
        try:
            return _DownloadStream(response.read())
        finally:
            response.close()
            response.release_conn()

    def delete_blob(self, delete_snapshots: str | None = None) -> None:
        self._client.remove_object(self._bucket, self._object_name)

    def exists(self) -> bool:
        try:
            self._client.stat_object(self._bucket, self._object_name)
            return True
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                return False
            raise


class _ContainerClient:
    def __init__(self, client: Minio, bucket: str):
        self._client = client
        self._bucket = bucket

    def list_blobs(self, name_starts_with: str | None = None) -> Iterator[_BlobProperties]:
        prefix = to_minio_object_key(name_starts_with or "")
        for obj in self._client.list_objects(self._bucket, prefix=prefix, recursive=True):
            yield _BlobProperties(name=from_minio_object_key(obj.object_name))

    def get_blob_client(self, blob: str | None = None, blob_name: str | None = None) -> _BlobClient:
        key = blob or blob_name
        if not key:
            raise ValueError("blob name is required")
        return _BlobClient(self._client, self._bucket, key)


class BlobServiceClient:
    """MinIO-backed stand-in for azure.storage.blob.BlobServiceClient."""

    def __init__(self, client: Minio):
        self._client = client

    @classmethod
    def from_connection_string(cls, connection_string: str | None) -> BlobServiceClient:
        return cls(_minio_client())

    def get_container_client(self, container_name: str) -> _ContainerClient:
        bucket = _clean_env(container_name) or container_name
        return _ContainerClient(self._client, bucket)

    def get_blob_client(self, *, container: str, blob: str) -> _BlobClient:
        return _BlobClient(self._client, container, blob)

    def create_container(
        self,
        container_name: str,
        public_access: str | None = None,
    ) -> _ContainerClient:
        bucket = _clean_env(container_name) or container_name
        if self._client.bucket_exists(bucket):
            raise ResourceExistsError(f"Bucket {bucket} already exists")
        self._client.make_bucket(bucket)
        return _ContainerClient(self._client, bucket)


def sync_directory_to_bucket(
    local_dir: str,
    bucket: str,
    prefix: str,
    *,
    client: Minio | None = None,
) -> int:
    """
    Upload all files under local_dir to bucket at prefix/.

    Used after GraphRAG file-based indexing to upload artifacts to MinIO.
    Returns the number of objects uploaded.
    """
    mc = client or _minio_client()
    prefix = prefix.strip("/")
    uploaded = 0
    for root, _, files in os.walk(local_dir):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, local_dir).replace("\\", "/")
            logical_key = f"{prefix}/{rel}" if prefix else rel
            key = to_minio_object_key(logical_key)
            mc.fput_object(bucket, key, full)
            uploaded += 1
    return uploaded
