"""
Monkey-patch GraphRAG's indexer ``OpenAIEmbeddingsLLM`` so NVIDIA NIM asymmetric models
receive ``extra_body.input_type`` (default passage); the upstream library does not pass this.

Applied only when launching indexing via ``graphrag_index_runner.py``.
"""

from __future__ import annotations

import os
from typing import Any


def apply_graphrag_index_nim_embedding_passage_patch() -> None:
    from graphrag.llm.openai import openai_embeddings_llm as mod

    cls = mod.OpenAIEmbeddingsLLM
    if getattr(cls, "_uniview_graphrag_nim_patch_applied", False):
        return
    setattr(cls, "_uniview_graphrag_nim_patch_applied", True)

    original = cls._execute_llm

    async def _wrapped(self: Any, input: Any, **kwargs: Any):
        raw = os.getenv("GRAPHRAG_INDEX_EMBEDDING_INPUT_TYPE")
        default_passage = "passage"
        it = (raw if raw is not None else default_passage).strip().lower()
        if it in ("", "none", "off"):
            return await original(self, input, **kwargs)
        mp = dict(kwargs.get("model_parameters") or {})
        eb = dict(mp.get("extra_body") or {})
        eb.setdefault("input_type", it)
        mp["extra_body"] = eb
        kwargs = {**kwargs, "model_parameters": mp}
        return await original(self, input, **kwargs)

    cls._execute_llm = _wrapped  # type: ignore[method-assign]
