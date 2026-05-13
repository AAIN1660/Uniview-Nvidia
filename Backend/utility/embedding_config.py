"""
Shared embedding configuration for Azure OpenAI vs NVIDIA NIM (OpenAI-compatible).

NVIDIA nv-embedqa-e5-v5: use EMBEDDING_BACKEND=nvidia and set NVIDIA_EMBEDDING_*.
See unified.env comments for VECTOR_SEARCH_DIMENSIONS (typically 1024 for E5-v5).
"""
from __future__ import annotations

import os
from typing import Any, Literal

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

load_dotenv("unified.env")

InputType = Literal["query", "passage"]


def _clean_env(value: str | None, default: str = "") -> str:
    value = value if value is not None else default
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


def embedding_backend() -> str:
    return _clean_env(os.getenv("EMBEDDING_BACKEND"), "azure").lower()


def embedding_model_id() -> str:
    if embedding_backend() == "nvidia":
        return _clean_env(os.getenv("NVIDIA_EMBEDDING_MODEL"), "nvidia/nv-embedqa-e5-v5")
    return _clean_env(os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL"))


def get_embedding_client() -> AzureOpenAI | OpenAI:
    if embedding_backend() == "nvidia":
        base = _clean_env(os.getenv("NVIDIA_EMBEDDING_BASE_URL"), "https://integrate.api.nvidia.com/v1")
        key = _clean_env(os.getenv("NVIDIA_EMBEDDING_API_KEY") or os.getenv("NVIDIA_API_KEY"))
        if not key:
            raise ValueError(
                "EMBEDDING_BACKEND=nvidia requires NVIDIA_EMBEDDING_API_KEY (or NVIDIA_API_KEY) in unified.env"
            )
        return OpenAI(base_url=base, api_key=key)
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_API_BASE"),
    )


def embedding_create_kwargs(input_type: InputType | None = None) -> dict[str, Any]:
    """NIM E5 models often expect input_type in the request body for best retrieval quality."""
    if embedding_backend() != "nvidia":
        return {}
    it = input_type or os.getenv("NVIDIA_EMBEDDING_INPUT_TYPE") or "query"
    it = str(it).strip().lower()
    if it not in ("query", "passage"):
        it = "query"
    return {"extra_body": {"input_type": it}}


def create_embedding_vector(
    client: AzureOpenAI | OpenAI,
    text: str,
    *,
    input_type: InputType | None = None,
) -> list[float]:
    """Single text embedding; uses model id from env."""
    model = embedding_model_id()
    kwargs = embedding_create_kwargs(input_type=input_type)
    inp = text if isinstance(text, str) else str(text)
    try:
        response = client.embeddings.create(input=inp, model=model, **kwargs)
        return response.data[0].embedding
    except Exception as exc:
        # Fallback for environments where NVIDIA /embeddings may be unavailable
        # for a given account/model. This keeps retrieval working instead of
        # failing the whole workflow.
        message = str(exc).lower()
        if embedding_backend() == "nvidia" and "404" in message:
            azure_client = AzureOpenAI(
                api_key=_clean_env(os.getenv("AZURE_OPENAI_API_KEY")),
                api_version=_clean_env(os.getenv("AZURE_OPENAI_API_VERSION")),
                azure_endpoint=_clean_env(os.getenv("AZURE_OPENAI_API_BASE")),
            )
            azure_model = _clean_env(os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL"))
            if not azure_model:
                raise
            response = azure_client.embeddings.create(input=inp, model=azure_model)
            return response.data[0].embedding
        raise
