# Object storage: MinIO only (Azure Blob removed)

All application blob I/O uses **MinIO** via `utility/blob_storage.py` and `utility/minio_blob_store.py`.

Azure Blob is **not** used anywhere in runtime code. The only remaining Azure Storage use is **queues** (`AZURE_STORAGE_CONNECTION_STRING`).

## 1. Start MinIO

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-minio-windows.ps1
```

Console: http://localhost:9001 (`minioadmin` / `minioadmin`)

## 2. Configure unified.env

```env
BLOB_STORAGE_CONTAINER_NAME=unifiedproddocs
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

Queues (unchanged, not blob):

```env
AZURE_STORAGE_CONNECTION_STRING=...your azure storage account...
```

## 3. Copy existing Azure blobs to MinIO (one-time)

Requires source Azure credentials (same account as before):

```powershell
cd Backend
.\.venv\Scripts\activate
pip install azure-storage-blob minio
python scripts/migrate_azure_blob_to_minio.py --dry-run
python scripts/migrate_azure_blob_to_minio.py
```

Object **keys are preserved** logically (same paths as in Azure). Colons (`:`) in names are encoded as `%3A` in MinIO (S3 does not allow `:` in keys); the app handles this automatically.

## 4. Restart backend

```powershell
uvicorn main:app --port 8000 --reload
```

Expect:

```text
[blob-storage] backend=minio endpoint=localhost:9000 bucket=unifiedproddocs
```

## What changed in code

| Before | After |
|--------|--------|
| `azure.storage.blob` in app code | `utility.blob_storage.get_blob_service_client()` |
| `BLOB_STORAGE_CONNECTION_STRING` for blobs | Removed; blobs use `MINIO_*` only |
| `BLOB_STORAGE_BACKEND` toggle | Removed; MinIO only |
| GraphRAG `settings.yaml` `type: blob` | `type: file` + sync to MinIO after index |

## Azure still used for (not blob)

- Azure Queue (`queue_service_app.py`, vector/graphrag workers)
- Azure AI Search, OpenAI, etc. (unchanged)
