"""
OpenAI-compatible chat completions for NVIDIA NIM (NeMo Agent Toolkit stack).
Used by the NAT-native orchestrator - no AutoGen dependency.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from openai import OpenAI

from utility.nemo_autogen_service import _clean_env, _normalize_base_url

_client_lock = threading.Lock()
_openai_client: OpenAI | None = None
_openai_client_key: tuple[str, str] | None = None


def _client() -> OpenAI:
    """
    Single shared OpenAI SDK client for all NIM calls.

    Reuses HTTP connections (TLS + pooling) across dozens of sequential completions,
    without changing prompts, agents, or orchestration logic.
    """
    global _openai_client, _openai_client_key
    base_url = _normalize_base_url(os.getenv("NVIDIA_BASE_URL"))
    api_key = _clean_env(os.getenv("NVIDIA_API_KEY"), "") or ""
    key = (base_url, api_key)
    with _client_lock:
        if _openai_client is None or _openai_client_key != key:
            _openai_client = OpenAI(base_url=base_url, api_key=api_key)
            _openai_client_key = key
        return _openai_client


def _model() -> str:
    return _clean_env(os.getenv("NVIDIA_MODEL"), "meta/llama-3.3-70b-instruct") or ""


def chat_completion(
    agent_name: str,
    system: str,
    user: str,
    agent_latency: dict[str, float],
    temperature: float = 0.1,
    timeout: float = 120.0,
) -> tuple[str, int]:
    """Returns (assistant_content, total_tokens). Updates agent_latency cumulative seconds."""
    t0 = time.time()
    client = _client()
    r = client.chat.completions.create(
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


def chat_completion_raw_messages(
    agent_name: str,
    messages: list[dict[str, Any]],
    agent_latency: dict[str, float],
    temperature: float = 0.1,
    timeout: float = 120.0,
) -> tuple[str, int]:
    """Multi-turn chat for agents that need prior steps in-context."""
    t0 = time.time()
    client = _client()
    r = client.chat.completions.create(
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
