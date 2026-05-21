"""Align process env with names expected by GraphRAG ``data/settings.yaml``."""

from __future__ import annotations

import os


def _clean(val: str | None) -> str:
    return (val or "").strip()


def _is_usable(val: str | None) -> bool:
    v = _clean(val)
    return bool(v) and not v.startswith("${")


def _first_set(*keys: str) -> str | None:
    for key in keys:
        v = _clean(os.getenv(key))
        if _is_usable(v):
            return v
    return None


def ensure_graphrag_index_env() -> None:
    """
    GraphRAG expands ``${OPENAI_API_BASE}`` etc. from the environment.

    ``unified.env`` defines ``GRAPH_RAG_OPENAI_*`` but not ``OPENAI_API_*``,
    which causes entity extraction to call Azure with a URL that has no scheme.
    """
    mappings: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("OPENAI_API_BASE", ("GRAPH_RAG_OPENAI_API_BASE", "AZURE_OPENAI_API_BASE")),
        ("OPENAI_BASE_URL", ("GRAPH_RAG_OPENAI_API_BASE", "AZURE_OPENAI_API_BASE")),
        ("OPENAI_API_KEY", ("GRAPH_RAG_OPENAI_API_KEY", "AZURE_OPENAI_API_KEY")),
        (
            "OPENAI_API_VERSION",
            ("GRAPH_RAG_OPENAI_API_VERSION", "AZURE_OPENAI_API_VERSION"),
        ),
    )
    for target, sources in mappings:
        if _is_usable(os.getenv(target)):
            continue
        value = _first_set(*sources)
        if value:
            os.environ[target] = value

    if not _is_usable(os.getenv("NVIDIA_API_KEY")):
        key = _first_set("NVIDIA_EMBEDDING_API_KEY", "NVIDIA_API_KEY")
        if key:
            os.environ["NVIDIA_API_KEY"] = key
