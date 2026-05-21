"""
GraphRAG query-time embeddings: NVIDIA NIM (OpenAI-compatible) vs Azure OpenAI.

Aligns with ``NVIDIA_EMBEDDING_*`` when using NIM. Indexing embeds corpus text with
``input_type=passage`` via ``graphrag_index_runner.py`` + ``graphrag_nim_index_embedding_patch``.
"""

from __future__ import annotations

import os

from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.llm.oai.typing import OpenaiApiType

from utility.embedding_config import embedding_backend
from utility.nemo_autogen_service import _clean_env, _normalize_base_url


def graphrag_embeddings_use_nim() -> bool:
    """
    If GRAPH_RAG_EMBEDDING_BACKEND is unset, follow ``EMBEDDING_BACKEND``: nvidia -> NIM
    embeddings for GraphRAG query + (with new settings.yaml) indexer.
    Set GRAPH_RAG_EMBEDDING_BACKEND=azure to force Azure embeddings for legacy indices.
    """
    v = (os.getenv("GRAPH_RAG_EMBEDDING_BACKEND") or "").strip().lower()
    if v in ("azure", "azure_openai", "legacy"):
        return False
    if v in ("nvidia", "nim", "openai", "openai_compatible"):
        return True
    return embedding_backend() == "nvidia"


def graphrag_nim_embedding_model_id() -> str:
    """Same model id used for indexer (settings.yaml ``NVIDIA_EMBEDDING_MODEL``)."""
    m = _clean_env(os.getenv("NVIDIA_EMBEDDING_MODEL"))
    if not m:
        m = _clean_env(os.getenv("GRAPH_RAG_EMBEDDING_MODEL_NAME"))
    return m or "nvidia/nv-embedqa-e5-v5"


class NvidiaGraphRAGQueryEmbedding(OpenAIEmbedding):
    """Injects asymmetric ``input_type`` for NVIDIA E5-style embedders (query side)."""

    def _embed_with_retry(self, text, **kwargs):
        it = (_clean_env(os.getenv("NVIDIA_EMBEDDING_INPUT_TYPE")) or "query").strip().lower()
        if it not in ("query", "passage"):
            it = "query"
        kwargs.setdefault("extra_body", {})
        kwargs["extra_body"].setdefault("input_type", it)
        return super()._embed_with_retry(text, **kwargs)

    async def _aembed_with_retry(self, text, **kwargs):
        it = (_clean_env(os.getenv("NVIDIA_EMBEDDING_INPUT_TYPE")) or "query").strip().lower()
        if it not in ("query", "passage"):
            it = "query"
        kwargs.setdefault("extra_body", {})
        kwargs["extra_body"].setdefault("input_type", it)
        return await super()._aembed_with_retry(text, **kwargs)


def create_graphrag_text_embedder(max_retries: int = 20) -> OpenAIEmbedding:
    """Build embedder compatible with LanceDB artifacts (must match indexer model + dim)."""
    if graphrag_embeddings_use_nim():
        base_raw = _clean_env(os.getenv("NVIDIA_EMBEDDING_BASE_URL"))
        base = base_raw if base_raw else _normalize_base_url(os.getenv("NVIDIA_BASE_URL"))
        key = _clean_env(os.getenv("NVIDIA_EMBEDDING_API_KEY") or os.getenv("NVIDIA_API_KEY"), "") or ""
        model = graphrag_nim_embedding_model_id()
        return NvidiaGraphRAGQueryEmbedding(
            api_key=key,
            api_base=base,
            api_version=None,
            model=model,
            deployment_name=model,
            api_type=OpenaiApiType.OpenAI,
            max_retries=max_retries,
        )

    gr_model = _clean_env(
        os.getenv("GRAPH_RAG_EMBEDDING_MODEL_NAME")
        or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL"),
        "text-embedding-3-small",
    )
    api_key = _clean_env(os.getenv("GRAPH_RAG_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"))
    api_base = _clean_env(os.getenv("GRAPH_RAG_OPENAI_API_BASE") or os.getenv("AZURE_OPENAI_API_BASE"))
    api_version = _clean_env(
        os.getenv("GRAPH_RAG_OPENAI_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION"),
        "2024-02-01",
    )
    return OpenAIEmbedding(
        api_key=api_key,
        api_base=api_base,
        api_version=api_version,
        api_type=OpenaiApiType.AzureOpenAI,
        model=gr_model,
        deployment_name=gr_model,
        max_retries=max_retries,
    )
