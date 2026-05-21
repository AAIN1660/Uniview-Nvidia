"""
OpenAI-compatible chat completions for NVIDIA NIM (NeMo Agent Toolkit stack).
Used by the NAT-native orchestrator - no AutoGen dependency.

The SDK class is named ``AsyncOpenAI`` but the client is pointed at the NVIDIA
NIM endpoint via ``NVIDIA_BASE_URL`` and authenticated with ``NVIDIA_API_KEY``.
All traffic stays on NIM; no call ever goes to api.openai.com.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Any

from openai import AsyncOpenAI, OpenAI

from utility.nemo_autogen_service import _clean_env, _normalize_base_url

_client_lock = asyncio.Lock()
_async_client: AsyncOpenAI | None = None
_async_client_key: tuple[str, str] | None = None

_sync_lock = threading.Lock()
_sync_client: OpenAI | None = None
_sync_client_key: tuple[str, str] | None = None


async def _client() -> AsyncOpenAI:
    """
    Single shared async NIM client for all completions.

    Reuses HTTP connections (TLS + pooling) across dozens of sequential
    completions without changing prompts, agents, or orchestration logic.
    The underlying transport is httpx.AsyncClient, which keeps connections
    warm to the NIM endpoint and frees the FastAPI event loop while waiting
    on the model.
    """
    global _async_client, _async_client_key
    base_url = _normalize_base_url(os.getenv("NVIDIA_BASE_URL"))
    api_key = _clean_env(os.getenv("NVIDIA_API_KEY"), "") or ""
    key = (base_url, api_key)
    async with _client_lock:
        if _async_client is None or _async_client_key != key:
            _async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
            _async_client_key = key
        return _async_client


def _model() -> str:
    return _clean_env(os.getenv("NVIDIA_MODEL"), "meta/llama-3.3-70b-instruct") or ""


def _sync_openai_client() -> OpenAI:
    """Shared sync client for code paths that run in a worker thread (e.g. asyncio.to_thread)."""
    global _sync_client, _sync_client_key
    base_url = _normalize_base_url(os.getenv("NVIDIA_BASE_URL"))
    api_key = _clean_env(os.getenv("NVIDIA_API_KEY"), "") or ""
    key = (base_url, api_key)
    with _sync_lock:
        if _sync_client is None or _sync_client_key != key:
            _sync_client = OpenAI(base_url=base_url, api_key=api_key)
            _sync_client_key = key
        return _sync_client


def chat_completion_sync(
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout: float = 120.0,
    model: str | None = None,
) -> str:
    """
    Blocking OpenAI-compatible chat completion against NVIDIA NIM.

    Uses ``NVIDIA_BASE_URL``, ``NVIDIA_API_KEY``, and ``NVIDIA_MODEL`` (unless
    ``model`` is passed).
    """
    client = _sync_openai_client()
    r = client.chat.completions.create(
        model=model or _model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return (r.choices[0].message.content or "").strip()


async def chat_completion(
    agent_name: str,
    system: str,
    user: str,
    agent_latency: dict[str, float],
    temperature: float = 0.1,
    timeout: float = 120.0,
) -> tuple[str, int]:
    """Returns (assistant_content, total_tokens). Updates agent_latency cumulative seconds."""
    t0 = time.time()
    client = await _client()
    r = await client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        timeout=timeout,
    )
    elapsed = time.time() - t0
    agent_latency[agent_name] = agent_latency.get(agent_name, 0.0) + elapsed
    text = (r.choices[0].message.content or "").strip()
    usage = getattr(r, "usage", None)
    tokens = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
    return text, tokens


async def chat_completion_raw_messages(
    agent_name: str,
    messages: list[dict[str, Any]],
    agent_latency: dict[str, float],
    temperature: float = 0.1,
    timeout: float = 120.0,
) -> tuple[str, int]:
    """Multi-turn chat for agents that need prior steps in-context."""
    t0 = time.time()
    client = await _client()
    r = await client.chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=temperature,
        timeout=timeout,
    )
    elapsed = time.time() - t0
    agent_latency[agent_name] = agent_latency.get(agent_name, 0.0) + elapsed
    text = (r.choices[0].message.content or "").strip()
    usage = getattr(r, "usage", None)
    tokens = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
    return text, tokens
