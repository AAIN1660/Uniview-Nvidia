import os
from typing import Any, Dict, List, Optional

from pymilvus import MilvusClient


def _zilliz_collection_name(explicit: Optional[str] = None) -> str:
    """Match utility.zilliz_ingestion.search_pdf_chunks_zilliz resolution order."""
    if explicit:
        return explicit
    return (
        os.getenv("ZILLIZ_COLLECTION_NAME")
        or os.getenv("ZILLIZ_COLLECTION")
        or "uniview_pdf_chunks"
    )


def _zilliz_vector_field() -> str:
    # Azure-shaped indexes used contentVector; Uniview PDF chunks use "embedding" (see Zilliz schema).
    return os.getenv("ZILLIZ_VECTOR_FIELD", "embedding")


def _zilliz_output_field_names() -> List[str]:
    raw = (os.getenv("ZILLIZ_OUTPUT_FIELDS") or "").strip()
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    return ["id", "text", "source_file", "chunk_index"]


def _zilliz_category_field() -> Optional[str]:
    """
    Scalar field used to filter by Cosmos category id.
    Leave unset (or set to none/false) when the collection has no category column
    (e.g. uniview_pdf_chunks: id, text, source_file, chunk_index, embedding).
    """
    raw = os.getenv("ZILLIZ_CATEGORY_FIELD")
    if raw is None:
        return None
    raw = raw.strip()
    if not raw or raw.lower() in ("none", "false", "0", "disabled", "-"):
        return None
    return raw


def _get_client() -> MilvusClient:
    uri = os.getenv("ZILLIZ_URI") or os.getenv("MILVUS_URI") or os.getenv("MILVUS_HOST")
    token = os.getenv("ZILLIZ_TOKEN") or os.getenv("MILVUS_TOKEN") or os.getenv("MILVUS_PASSWORD")
    if not uri:
        raise RuntimeError("Missing ZILLIZ_URI (public endpoint).")
    if not token:
        raise RuntimeError("Missing ZILLIZ_TOKEN (cluster token).")
    return MilvusClient(uri=uri, token=token)


def insert_chunks(records: List[Dict[str, Any]], collection_name: Optional[str] = None) -> Dict[str, Any]:
    client = _get_client()
    col = _zilliz_collection_name(collection_name)
    return client.insert(collection_name=col, data=records)


def search_chunks(
    query_vector: List[float],
    top_k: int = 3,
    category_ids: Optional[List[str]] = None,
    collection_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    col = _zilliz_collection_name(collection_name)
    vector_field = _zilliz_vector_field()
    out_fields = _zilliz_output_field_names()

    expr = None
    cat_field = _zilliz_category_field()
    if category_ids and cat_field:
        quoted = ", ".join([f'\"{c}\"' for c in category_ids])
        expr = f"{cat_field} in [{quoted}]"

    res = client.search(
        collection_name=col,
        data=[query_vector],
        anns_field=vector_field,
        limit=top_k,
        output_fields=out_fields,
        filter=expr,
    )
    # MilvusClient returns list-of-list; take first query's hits
    hits = res[0] if res else []
    out: List[Dict[str, Any]] = []
    for h in hits:
        entity = h.get("entity") or {}
        out.append(
            {
                "score": h.get("score"),
                **entity,
            }
        )
    return out


def delete_chunks_by_ids(
    ids: List[str], collection_name: Optional[str] = None
) -> Dict[str, Any]:
    client = _get_client()
    col = _zilliz_collection_name(collection_name)
    clean_ids = [str(i).strip() for i in (ids or []) if str(i).strip()]
    if not clean_ids:
        return {"deleted_count": 0}
    quoted = ", ".join([f'"{i}"' for i in clean_ids])
    expr = f"id in [{quoted}]"
    return client.delete(collection_name=col, filter=expr)

