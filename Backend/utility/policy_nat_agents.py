"""
NAT / NIM policy agents (JSON decisions only ).

Controlled by ENABLE_NAT_POLICY_AGENTS and per-phase overrides in unified.env.
"""

from __future__ import annotations

import json
import os
from typing import Any

from utility.nim_chat_client import chat_completion


def _truthy(raw: str | None, default: bool = True) -> bool:
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def nat_policy_master_enabled() -> bool:
    return _truthy(os.getenv("ENABLE_NAT_POLICY_AGENTS"), default=True)


def nat_input_policy_enabled() -> bool:
    v = os.getenv("ENABLE_NAT_INPUT_POLICY")
    if v is not None and str(v).strip() != "":
        return _truthy(v, default=True)
    return nat_policy_master_enabled()


def nat_grounding_policy_enabled() -> bool:
    v = os.getenv("ENABLE_NAT_GROUNDING_POLICY")
    if v is not None and str(v).strip() != "":
        return _truthy(v, default=True)
    return nat_policy_master_enabled()


def nat_output_policy_enabled() -> bool:
    v = os.getenv("ENABLE_NAT_OUTPUT_POLICY")
    if v is not None and str(v).strip() != "":
        return _truthy(v, default=True)
    return nat_policy_master_enabled()


def nat_policy_fail_open() -> bool:
    """If True, unparsable policy JSON is treated as allowed (log only)."""
    return _truthy(os.getenv("NAT_POLICY_FAIL_OPEN"), default=True)


def ctx_to_grounding_snippets(
    ctx: Any,
    *,
    max_chunks: int = 8,
    max_chars_per: int = 1200,
) -> str:
    """Flatten extract_context() payload into short text for the grounding policy agent."""
    if not isinstance(ctx, dict):
        return ""
    parts: list[str] = []
    vc = ctx.get("vector_context") or {}
    for i, line in enumerate(vc.get("chunks") or []):
        if i >= max_chunks:
            break
        s = str(line).strip()[:max_chars_per]
        if s:
            parts.append(f"[vector {i + 1}]\n{s}")
    gc = ctx.get("graph_context") or {}
    for i, line in enumerate(gc.get("chunks") or []):
        if len(parts) >= max_chunks:
            break
        s = str(line).strip()[:max_chars_per]
        if s:
            parts.append(f"[graph {i + 1}]\n{s}")
    return "\n\n".join(parts)


def _parse_policy_json(content: str) -> dict[str, Any]:
    from utility import inference as inf

    obj = inf.parse_agent_content_json(content)
    if not isinstance(obj, dict):
        return {}
    return obj


def _normalize_allowed(obj: dict[str, Any]) -> tuple[bool, str, str]:
    """
    Returns (allowed, message, redacted_or_empty_text).
    Model should emit allowed: bool, message: str, optional redacted_text for output phase.
    """
    allowed = obj.get("allowed", True)
    if isinstance(allowed, str):
        allowed = allowed.strip().lower() in ("true", "1", "yes")
    else:
        allowed = bool(allowed)
    message = str(obj.get("message") or obj.get("reason") or "").strip()
    redacted = str(obj.get("redacted_text") or obj.get("text") or "").strip()
    return allowed, message, redacted


async def run_nat_input_policy(
    query: str,
    system_prompt: str,
    agent_latency: dict[str, float],
) -> tuple[dict[str, Any], int]:
    """
    Returns ({"allowed": bool, "message": str, "raw": str}, tokens).
    """
    user = json.dumps({"question": query}, ensure_ascii=False)
    raw, tok = await chat_completion(
        "nat_input_policy",
        system_prompt,
        user,
        agent_latency,
        temperature=0.0,
    )
    parsed = _parse_policy_json(raw)
    if not parsed:
        if nat_policy_fail_open():
            return {"allowed": True, "message": "", "raw": raw}, tok
        return {
            "allowed": False,
            "message": "Policy review did not return a valid decision; request blocked.",
            "raw": raw,
        }, tok
    allowed, message, _ = _normalize_allowed(parsed)
    return {"allowed": allowed, "message": message or "This request is not allowed under policy.", "raw": raw}, tok


async def run_nat_grounding_policy(
    question: str,
    context_snippets: str,
    system_prompt: str,
    agent_latency: dict[str, float],
) -> tuple[dict[str, Any], int]:
    user = json.dumps(
        {"question": question, "retrieved_context_excerpts": context_snippets},
        ensure_ascii=False,
    )
    raw, tok = await chat_completion(
        "nat_grounding_policy",
        system_prompt,
        user,
        agent_latency,
        temperature=0.0,
    )
    parsed = _parse_policy_json(raw)
    if not parsed:
        if nat_policy_fail_open():
            return {"allowed": True, "message": "", "raw": raw}, tok
        return {
            "allowed": False,
            "message": "Grounding policy did not return a valid decision; blocking for safety.",
            "raw": raw,
        }, tok
    allowed, message, _ = _normalize_allowed(parsed)
    return {
        "allowed": allowed,
        "message": message
        or "The retrieved information does not appear sufficient to answer reliably.",
        "raw": raw,
    }, tok


async def run_nat_output_policy(
    query: str,
    answer_text: str,
    system_prompt: str,
    agent_latency: dict[str, float],
) -> tuple[dict[str, Any], int]:
    user = json.dumps(
        {"question": query, "draft_answer": answer_text[:24000]},
        ensure_ascii=False,
    )
    raw, tok = await chat_completion(
        "nat_output_policy",
        system_prompt,
        user,
        agent_latency,
        temperature=0.0,
    )
    parsed = _parse_policy_json(raw)
    if not parsed:
        if nat_policy_fail_open():
            return {"allowed": True, "message": "", "text": answer_text, "raw": raw}, tok
        return {
            "allowed": False,
            "message": "Output policy did not return a valid decision; response withheld.",
            "text": answer_text,
            "raw": raw,
        }, tok
    allowed, message, redacted = _normalize_allowed(parsed)
    if not allowed:
        block_msg = message or "This response was blocked by output policy."
        return {
            "allowed": False,
            "message": block_msg,
            "text": block_msg,
            "raw": raw,
        }, tok
    out_text = redacted if redacted else answer_text
    return {
        "allowed": True,
        "message": message,
        "text": out_text,
        "raw": raw,
    }, tok
