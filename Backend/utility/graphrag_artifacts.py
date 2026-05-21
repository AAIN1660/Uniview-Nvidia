"""
GraphRAG blob paths, per-category LanceDB layout, and embedding dimension checks.
"""

from __future__ import annotations

import os
from typing import Any


def _clean_env_val(v: str | None) -> str:
    if v is None:
        return ""
    s = str(v).strip().strip('"').strip("'")
    return s


def graphrag_embeddings_use_nim() -> bool:
    from utility.graphrag_text_embedder import graphrag_embeddings_use_nim as _use_nim

    return _use_nim()


def expected_graph_embedding_dim() -> int:
    """Query/indexer dimension for the active GraphRAG embedding backend."""
    if graphrag_embeddings_use_nim():
        try:
            return int(_clean_env_val(os.getenv("VECTOR_SEARCH_DIMENSIONS")) or "1024")
        except ValueError:
            return 1024
    return 1536


def resolve_graph_artifacts_folder(graphrag_category: str | None) -> str:
    """
    Blob prefix under BLOB_STORAGE_CONTAINER_NAME, e.g.
    ``graphragoutput/<category-id>/artifacts``.
    """
    folder_override = _clean_env_val(os.getenv("GRAPH_RAG_ARTIFACTS_FOLDER"))
    cat = _clean_env_val(graphrag_category) if graphrag_category else ""
    default_cat = _clean_env_val(os.getenv("GRAPH_RAG_DEFAULT_CATEGORY_ID"))
    if folder_override:
        return folder_override.rstrip("/")
    if cat:
        return f"graphragoutput/{cat}/artifacts"
    if default_cat:
        return f"graphragoutput/{default_cat}/artifacts"
    raise ValueError(
        "GraphRAG blob path unresolved: pass category on the request, or set "
        "GRAPH_RAG_ARTIFACTS_FOLDER or GRAPH_RAG_DEFAULT_CATEGORY_ID in unified.env."
    )


def graph_lancedb_uri(folder_path: str) -> str:
    """Isolated LanceDB directory per artifact folder (avoids 1536/1024 cross-talk)."""
    safe = folder_path.replace("\\", "/").strip("/").replace("/", "__")
    return os.path.join(os.getcwd(), "graphragoutput", "lancedb", safe)


def validate_entity_embedding_dims(entities: list[Any], expected: int, folder_path: str) -> None:
    """Fail fast when blob artifacts were indexed with a different embedding model."""
    for ent in entities:
        emb = getattr(ent, "description_embedding", None)
        if emb:
            got = len(emb)
            if got != expected:
                backend = "NVIDIA NIM" if graphrag_embeddings_use_nim() else "Azure OpenAI"
                raise ValueError(
                    f"GraphRAG artifact embeddings are {got}-dimensional but the active "
                    f"backend ({backend}) expects {expected}-dimensional vectors "
                    f"(blob folder: {folder_path}). "
                    "Re-index this category with graph_rag=true and "
                    "graphrag_index_runner.py (NIM passage embeddings in data/settings.yaml)."
                )
            print(
                f"[GraphRAG] artifact embedding dim OK ({got}) for {folder_path}",
                flush=True,
            )
            return
    print(
        f"[GraphRAG] warning: no description_embedding vectors in artifacts at {folder_path}",
        flush=True,
    )
