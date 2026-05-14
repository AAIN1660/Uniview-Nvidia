import logging
import os
from typing import Any, Dict, List, Optional

from pymilvus import AnnSearchRequest, MilvusClient, RRFRanker

logger = logging.getLogger(__name__)


def _clean(value: Optional[str]) -> str:
    """
    Strip whitespace AND surrounding quotes from env values.

    The PowerShell-based ``unified.env`` loader (`Get-Content | ForEach-Object`)
    does not unquote values, so an entry like  ZILLIZ_VECTOR_FIELD="embedding"
    ends up in os.environ as the literal string  "embedding"  (quotes included).
    Without this strip, Milvus search would be issued with anns_field='"embedding"'
    and reject the query as `fieldName("embedding") not found`.
    """
    if value is None:
        return ""
    return value.strip().strip("\"").strip("'")


def _zilliz_collection_name(explicit: Optional[str] = None) -> str:
    """Match utility.zilliz_ingestion.search_pdf_chunks_zilliz resolution order."""
    if explicit:
        return _clean(explicit)
    return (
        _clean(os.getenv("ZILLIZ_COLLECTION_NAME"))
        or _clean(os.getenv("ZILLIZ_COLLECTION"))
        or "uniview_pdf_chunks"
    )


def _has_sparse_field(client: MilvusClient, collection_name: str) -> bool:
    """
    True if the collection schema has a `sparse` field (BM25 hybrid eligible).

    Old collections created before the BM25 migration don't have this field,
    so hybrid_search would fail. We fall back to dense-only in that case.
    """
    try:
        desc = client.describe_collection(collection_name=collection_name)
        fields = desc.get("fields", []) if isinstance(desc, dict) else []
        return any(f.get("name") == "sparse" for f in fields)
    except Exception as e:
        logger.warning("describe_collection failed for %s: %s", collection_name, e)
        return False


def _zilliz_vector_field() -> str:
    # Azure-shaped indexes used contentVector; Uniview PDF chunks use "embedding" (see Zilliz schema).
    return _clean(os.getenv("ZILLIZ_VECTOR_FIELD")) or "embedding"


def _zilliz_output_field_names() -> List[str]:
    raw = _clean(os.getenv("ZILLIZ_OUTPUT_FIELDS"))
    if raw:
        return [_clean(p) for p in raw.split(",") if _clean(p)]
    return ["id", "text", "source_file", "chunk_index"]


def _get_client() -> MilvusClient:
    uri = (
        _clean(os.getenv("ZILLIZ_URI"))
        or _clean(os.getenv("MILVUS_URI"))
        or _clean(os.getenv("MILVUS_HOST"))
    )
    token = (
        _clean(os.getenv("ZILLIZ_TOKEN"))
        or _clean(os.getenv("MILVUS_TOKEN"))
        or _clean(os.getenv("MILVUS_PASSWORD"))
    )
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
    query_text: Optional[str] = None,
    top_k: int = 3,
    category_ids: Optional[List[str]] = None,
    collection_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top-K chunks for a question.

    When the collection has a ``sparse`` BM25 field AND ``query_text`` is
    provided, performs **hybrid search**: dense ANN + BM25 keyword, fused
    via Reciprocal Rank Fusion (RRF). This mirrors what Azure AI Search
    did internally via `query_type=SEMANTIC` + RRF, but on the NVIDIA-
    recommended Milvus stack.

    Falls back to dense-only when:
      - the collection schema has no ``sparse`` field (pre-migration data)
      - ``query_text`` is empty
      - ``ZILLIZ_ENABLE_HYBRID_SEARCH=false`` is set
      - hybrid_search throws (e.g. serverless tier lacks BM25 support)
    """
    client = _get_client()
    col = _zilliz_collection_name(collection_name)
    vector_field = _zilliz_vector_field()
    out_fields = _zilliz_output_field_names()

    expr = None
    if category_ids:
        cat_field = _clean(os.getenv("ZILLIZ_CATEGORY_FIELD")) or "category"
        quoted = ", ".join([f'\"{c}\"' for c in category_ids])
        expr = f"{cat_field} in [{quoted}]"

    enable_hybrid = (
        (_clean(os.getenv("ZILLIZ_ENABLE_HYBRID_SEARCH")) or "true").lower() == "true"
        and bool(query_text and query_text.strip())
        and _has_sparse_field(client, col)
    )

    if enable_hybrid:
        try:
            dense_req = AnnSearchRequest(
                data=[query_vector],
                anns_field=vector_field,
                param={"metric_type": "COSINE"},
                limit=top_k,
                expr=expr,
            )
            sparse_req = AnnSearchRequest(
                data=[query_text],
                anns_field="sparse",
                param={"metric_type": "BM25"},
                limit=top_k,
                expr=expr,
            )
            res = client.hybrid_search(
                collection_name=col,
                reqs=[dense_req, sparse_req],
                ranker=RRFRanker(k=60),
                limit=top_k,
                output_fields=out_fields,
            )
            hits = res[0] if res else []
            return [
                {"score": h.get("score"), **(h.get("entity") or {})}
                for h in hits
            ]
        except Exception as e:
            logger.warning(
                "hybrid_search failed (%s); falling back to dense-only", e
            )
            # Fall through to dense-only below.

    # Dense-only (legacy behavior, also used for pre-BM25 collections)
    res = client.search(
        collection_name=col,
        data=[query_vector],
        anns_field=vector_field,
        limit=top_k,
        output_fields=out_fields,
        filter=expr,
    )
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

