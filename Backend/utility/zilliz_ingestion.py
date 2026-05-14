"""
Step 1 ingestion: PDF → extract text → chunk (300–500 tokens) → NVIDIA embed → Zilliz/Milvus.

Uses unified.env: EMBEDDING_BACKEND=nvidia, NVIDIA_EMBEDDING_*, VECTOR_SEARCH_DIMENSIONS,
and ZILLIZ_* or MILVUS_* for the vector store.
"""
from __future__ import annotations

import io
import logging
import os
import uuid
from typing import Any

import tiktoken
from dotenv import load_dotenv

load_dotenv("unified.env")

logger = logging.getLogger(__name__)


def _vector_dim() -> int:
    return int(os.getenv("VECTOR_SEARCH_DIMENSIONS", "1024"))


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Step 1a: PDF → text. Prefer unstructured layout; fall back to PyMuPDF (fitz).
    """
    try:
        from unstructured.partition.pdf import partition_pdf

        file_stream = io.BytesIO(pdf_bytes)
        elements = partition_pdf(
            file=file_stream,
            strategy="hi_res",
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=10000,
            combine_text_under_n_chars=2000,
            new_after_n_chars=6000,
        )
        parts: list[str] = []
        for el in elements:
            t = getattr(el, "text", None) or ""
            if t.strip():
                parts.append(t.strip())
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning("unstructured PDF parse failed, using PyMuPDF: %s", e)
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            return "\n\n".join(page.get_text() for page in doc)
        finally:
            doc.close()


def chunk_text_by_token_budget(
    text: str,
    *,
    min_tokens: int = 300,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    encoding_name: str = "cl100k_base",
) -> list[str]:
    """
    Step 1b: Chunking in the 300–500 token range (tiktoken counts as a practical proxy).

    Sliding windows: each segment is at most max_tokens; when not at EOF, tries to
    keep at least min_tokens per segment; overlap preserves cross-boundary context.
    """
    if min_tokens > max_tokens:
        raise ValueError("min_tokens must be <= max_tokens")
    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text or "")
    if not tokens:
        return []

    overlap = min(max(0, overlap_tokens), max_tokens // 2)
    chunks: list[str] = []
    i = 0
    n = len(tokens)

    while i < n:
        j = min(i + max_tokens, n)
        segment = tokens[i:j]
        if j < n and len(segment) < min_tokens:
            j = min(i + min_tokens, n)
            segment = tokens[i:j]
        decoded = enc.decode(segment).strip()
        if decoded:
            chunks.append(decoded)
        if j >= n:
            break
        next_i = j - overlap
        if next_i <= i:
            next_i = j
        i = next_i

    return chunks


def _embed_passages(texts: list[str]) -> tuple[list[list[float]], int]:
    """Step 1c: NVIDIA (or Azure) embeddings via shared embedding_config."""
    from utility.embedding_config import (
        create_embedding_vector,
        embedding_backend,
        get_embedding_client,
    )

    client = get_embedding_client()
    vectors: list[list[float]] = []
    for t in texts:
        if embedding_backend() == "nvidia":
            v = create_embedding_vector(client, t, input_type="passage")
        else:
            v = create_embedding_vector(client, t)
        vectors.append(v)
    return vectors, 0


def _connect_milvus() -> None:
    from pymilvus import connections

    uri = (os.getenv("ZILLIZ_URI") or "").strip()
    token = (os.getenv("ZILLIZ_TOKEN") or "").strip()
    host = (os.getenv("MILVUS_HOST") or "127.0.0.1").strip()
    port = (os.getenv("MILVUS_PORT") or "19530").strip()

    try:
        if uri and token:
            connections.connect(alias="default", uri=uri, token=token)
            logger.info("Connected to Zilliz/Milvus via URI")
        else:
            connections.connect(alias="default", host=host, port=port)
            logger.info("Connected to Milvus at %s:%s", host, port)
    except Exception as e:
        if "already connected" in str(e).lower() or "repeatedly connect" in str(e).lower():
            return
        raise


def _dense_index_params() -> dict[str, Any]:
    """
    Pick dense ANN index based on ZILLIZ_INDEX_TYPE.

    Default: AUTOINDEX (CPU; safe everywhere, including Zilliz Cloud serverless).
    Set ZILLIZ_INDEX_TYPE=GPU_CAGRA on self-hosted Milvus GPU build (or Zilliz
    Cloud Dedicated GPU cluster) for the NVIDIA-native cuVS graph index — gives
    the same HNSW-style "navigable graph" semantics but built on the GPU.

    Other supported values: HNSW, IVF_FLAT, GPU_IVF_FLAT, GPU_IVF_PQ.
    """
    idx = (os.getenv("ZILLIZ_INDEX_TYPE") or "AUTOINDEX").strip().upper()
    if idx == "GPU_CAGRA":
        return {
            "metric_type": "COSINE",
            "index_type":  "GPU_CAGRA",
            "params": {
                "intermediate_graph_degree": 64,
                "graph_degree": 32,
                "build_algo": "NN_DESCENT",
            },
        }
    if idx == "HNSW":
        return {
            "metric_type": "COSINE",
            "index_type":  "HNSW",
            "params": {"M": 16, "efConstruction": 200},
        }
    # AUTOINDEX / GPU_IVF_FLAT / GPU_IVF_PQ / IVF_FLAT — pass through with empty params
    return {"metric_type": "COSINE", "index_type": idx, "params": {}}


def ensure_collection(collection_name: str, dim: int) -> Any:
    """
    Create collection + indexes if missing.

    Schema (new collections):
      - dense  `embedding` field   → ZILLIZ_INDEX_TYPE (default AUTOINDEX)
      - sparse `sparse`    field   → BM25 inverted index, fed by built-in BM25 function on `text`

    Old collections (without `sparse`) are loaded as-is. Hybrid search in
    zilliz_client.search_chunks gracefully falls back to dense-only when the
    sparse field is missing — you only get the BM25 hybrid upgrade after a
    fresh ingest into a new collection.
    """
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        Function,
        FunctionType,
        utility,
    )
    from pymilvus.exceptions import MilvusException

    if utility.has_collection(collection_name):
        col = Collection(collection_name)
        col.load()
        return col

    enable_bm25 = (os.getenv("ZILLIZ_ENABLE_BM25", "true").strip().lower() == "true")

    fields = [
        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=512,
        ),
        FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=enable_bm25,  # required for BM25 function
        ),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    if enable_bm25:
        fields.append(
            FieldSchema(name="sparse", dtype=DataType.SPARSE_FLOAT_VECTOR)
        )

    schema = CollectionSchema(fields, description="Uniview PDF chunks (dense + BM25 sparse)")

    if enable_bm25:
        # BM25 function auto-populates `sparse` from `text` at insert time.
        schema.add_function(
            Function(
                name="bm25_fn",
                function_type=FunctionType.BM25,
                input_field_names=["text"],
                output_field_names=["sparse"],
            )
        )

    collection = Collection(collection_name, schema)

    # Dense ANN index (configurable: AUTOINDEX default, GPU_CAGRA when GPU available)
    dense_params = _dense_index_params()
    try:
        collection.create_index(field_name="embedding", index_params=dense_params)
    except MilvusException as e:
        logger.warning(
            "Dense index create failed for %s (%s); falling back to AUTOINDEX",
            dense_params.get("index_type"),
            e,
        )
        try:
            collection.create_index(
                field_name="embedding",
                index_params={"metric_type": "COSINE", "index_type": "AUTOINDEX", "params": {}},
            )
        except MilvusException as e2:
            logger.warning("Fallback AUTOINDEX also failed: %s", e2)

    # Sparse BM25 inverted index (for hybrid keyword search)
    if enable_bm25:
        try:
            collection.create_index(
                field_name="sparse",
                index_params={
                    "metric_type": "BM25",
                    "index_type":  "SPARSE_INVERTED_INDEX",
                    "params": {"bm25_k1": 1.2, "bm25_b": 0.75},
                },
            )
        except MilvusException as e:
            logger.warning("BM25 sparse index create note (may already exist): %s", e)

    collection.load()
    return collection


def ingest_pdf_bytes_to_zilliz(
    pdf_bytes: bytes,
    *,
    source_name: str = "document.pdf",
    collection_name: str | None = None,
) -> dict[str, Any]:
    """
    Full pipeline: extract → chunk → embed → insert.

    Returns a small result dict with chunk count and ids.
    """
    collection_name = collection_name or (
        os.getenv("ZILLIZ_COLLECTION_NAME")
        or os.getenv("ZILLIZ_COLLECTION")
        or "uniview_pdf_chunks"
    )
    min_t = int(os.getenv("INGEST_CHUNK_TOKENS_MIN", "300"))
    max_t = int(os.getenv("INGEST_CHUNK_TOKENS_MAX", "500"))
    overlap = int(os.getenv("INGEST_CHUNK_OVERLAP_TOKENS", "50"))

    use_nemo_extraction = os.getenv("USE_NEMO_EXTRACTION", "true").strip().lower() == "true"

    if use_nemo_extraction:
        from utility.nemo_extraction import extract_with_nemo

        raw_chunks = extract_with_nemo(pdf_bytes, source_name=source_name)
        chunks = [
            c.get("content", "").strip()
            for c in raw_chunks
            if c.get("content", "").strip()
        ]
        if not chunks:
            raise ValueError("No text chunks produced by NeMo extraction")
    else:
        text = extract_text_from_pdf_bytes(pdf_bytes)
        if not text.strip():
            raise ValueError("No text extracted from PDF")

        chunks = chunk_text_by_token_budget(
            text, min_tokens=min_t, max_tokens=max_t, overlap_tokens=overlap
        )
        if not chunks:
            raise ValueError("Chunking produced no segments")

    vectors, _ = _embed_passages(chunks)
    dim = _vector_dim()
    if len(vectors[0]) != dim:
        logger.warning(
            "Embedding dim %s != VECTOR_SEARCH_DIMENSIONS %s; fix unified.env",
            len(vectors[0]),
            dim,
        )

    _connect_milvus()
    col = ensure_collection(collection_name, dim)

    base = uuid.uuid4().hex[:12]
    ids = [f"{base}_{i}" for i in range(len(chunks))]
    texts = [c[:65530] for c in chunks]
    sources = [source_name[:1020]] * len(chunks)
    indices = list(range(len(chunks)))

    col.insert([ids, texts, sources, indices, vectors])
    col.flush()

    return {
        "collection": collection_name,
        "source_file": source_name,
        "chunks": len(chunks),
        "ids": ids,
    }


def search_pdf_chunks_zilliz(
    query_text: str,
    *,
    top_k: int = 3,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Vector retrieval: NVIDIA embeddings → Zilliz/Milvus → chunks.

    Returns a list of records shaped like:
        {"sourcepage": <source_file>, "content": <chunk text>}
    so that the rest of the RAG pipeline can stay unchanged.
    """
    from pymilvus import Collection
    from utility.embedding_config import (
        create_embedding_vector,
        embedding_backend,
        get_embedding_client,
    )

    if not query_text or not query_text.strip():
        return []

    collection_name = collection_name or (
        os.getenv("ZILLIZ_COLLECTION_NAME")
        or os.getenv("ZILLIZ_COLLECTION")
        or "uniview_pdf_chunks"
    )

    client = get_embedding_client()
    if embedding_backend() == "nvidia":
        query_vec = create_embedding_vector(client, query_text, input_type="query")
    else:
        query_vec = create_embedding_vector(client, query_text)

    _connect_milvus()
    col = ensure_collection(collection_name, len(query_vec))

    search_params = {
        "metric_type": "COSINE",
        "params": {},
    }

    results = col.search(
        data=[query_vec],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["text", "source_file", "chunk_index"],
    )

    hits = results[0] if results else []
    out: list[dict[str, Any]] = []
    for h in hits:
        src = h.get("source_file") or ""
        txt = h.get("text") or ""
        out.append(
            {
                "sourcepage": str(src),
                "content": str(txt),
            }
        )
    return out
