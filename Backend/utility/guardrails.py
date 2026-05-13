"""
NVIDIA NeMo Guardrails integration.
Single-model Guardrails using:
- nvidia/llama-3.1-nemoguard-8b-content-safety
"""

import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv("unified.env")

# Environment configs
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL",
    "https://integrate.api.nvidia.com/v1"
)

ENABLE_GUARDRAILS = (
    os.getenv("ENABLE_GUARDRAILS", "true")
    .strip()
    .lower() == "true"
)

GUARDRAIL_MODEL = os.getenv(
    "NVIDIA_GUARDRAIL_MODEL",
    "nvidia/llama-3.1-nemoguard-8b-content-safety"
)

# Messages
UNSAFE_CONTENT_MSG = (
    "I'm sorry, I cannot respond to that request "
    "as it contains unsafe content."
)

UNSAFE_OUTPUT_MSG = (
    "The generated response was flagged for safety. "
    "Please rephrase your question."
)

# OpenAI client
_client = None


def _get_client() -> OpenAI:
    """
    Create/reuse NVIDIA OpenAI-compatible client
    """

    global _client

    if _client is None:

        _client = OpenAI(
            api_key=NVIDIA_API_KEY,
            base_url=NVIDIA_BASE_URL,
        )

    return _client


def _norm_key(key: str) -> str:
    return re.sub(r"\s+", "_", str(key).strip().lower())


def _interpret_safety_response(raw: str, role: str) -> bool:
    """
    Map guardrail model output to a boolean.

    The NVIDIA content-safety model often returns JSON like
    {"user safety": "safe", "response safety": "unsafe"} instead of a
    single token. We honor explicit classifications and fail closed only
    when nothing decisive is present.
    """

    text = raw.strip()
    lowered = text.lower()

    if lowered == "safe":
        return True
    if lowered == "unsafe":
        return False

    if re.search(r"\bunsafe\b", lowered):
        return False

    user_norm_keys = frozenset(
        {"user_safety", "input_safety", "input", "user"}
    )
    response_norm_keys = frozenset(
        {"response_safety", "output_safety", "output", "assistant"}
    )

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        by_norm = {_norm_key(k): v for k, v in data.items()}

        priority_keys = (
            user_norm_keys if role == "user" else response_norm_keys
        )

        for nk in priority_keys:
            if nk not in by_norm:
                continue
            val = str(by_norm[nk]).strip().lower()
            if val == "unsafe":
                return False
            if val == "safe":
                return True

        for nk, val in by_norm.items():
            if nk in user_norm_keys | response_norm_keys:
                v = str(val).strip().lower()
                if v == "unsafe":
                    return False

        str_vals = [
            str(v).strip().lower()
            for v in by_norm.values()
            if isinstance(v, str)
        ]
        if str_vals and all(v == "safe" for v in str_vals):
            return True

    primary_field = "user safety" if role == "user" else "response safety"
    secondary_field = "response safety" if role == "user" else "user safety"

    for field in (primary_field, secondary_field):
        m = re.search(
            rf'"{re.escape(field)}"\s*:\s*"([^"]+)"',
            text,
            flags=re.IGNORECASE,
        )
        if m:
            val = m.group(1).strip().lower()
            if val == "unsafe":
                return False
            if val == "safe":
                return True

    return False


def check_content_safety(
    text: str,
    role: str = "user"
) -> dict:
    """
    Check if text is safe using NeMo Guardrails model.

    Returns:
        {
            "safe": bool,
            "reason": str
        }
    """

    try:

        print("\n====================================")
        print("[Guardrails] Running Safety Check")
        print("====================================")
        print(f"[Guardrails] Role: {role}")
        print(f"[Guardrails] Text: {text}")

        safety_prompt = f"""
Classify the following message.

Return ONLY ONE WORD:
safe
or
unsafe

Message:
{text}
"""

        response = _get_client().chat.completions.create(
            model=GUARDRAIL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict content safety classifier. "
                        "Reply ONLY with 'safe' or 'unsafe'."
                    ),
                },
                {
                    "role": "user",
                    "content": safety_prompt,
                },
            ],
            max_tokens=256,
            temperature=0.0,
        )

        raw = (response.choices[0].message.content or "").strip()

        print(f"\n[Guardrails Raw Result] -> {raw}\n")

        is_safe = _interpret_safety_response(raw, role)

        print(f"[Guardrails Parsed Safe] -> {is_safe}")

        return {
            "safe": is_safe,
            "reason": raw,
        }

    except Exception as e:

        print(f"[Guardrails] Safety check failed: {e}")

        # Fail closed
        return {
            "safe": False,
            "reason": "check_failed",
        }


def check_input(query: str) -> dict:
    """
    Input guardrail check.
    """

    if not ENABLE_GUARDRAILS:

        return {"allowed": True}

    print("\n====================================")
    print("[Guardrails] Checking INPUT")
    print("====================================")

    safety = check_content_safety(
        query,
        role="user"
    )

    if not safety["safe"]:

        print("[Guardrails] INPUT BLOCKED")

        return {
            "allowed": False,
            "message": UNSAFE_CONTENT_MSG,
        }

    print("[Guardrails] INPUT ALLOWED")

    return {"allowed": True}


def check_output(response_text: str) -> dict:
    """
    Output guardrail check.
    """

    if not ENABLE_GUARDRAILS:

        return {
            "allowed": True,
            "text": response_text,
        }

    print("\n====================================")
    print("[Guardrails] Checking OUTPUT")
    print("====================================")

    safety = check_content_safety(
        response_text,
        role="assistant"
    )

    if not safety["safe"]:

        print("[Guardrails] OUTPUT BLOCKED")

        return {
            "allowed": False,
            "text": UNSAFE_OUTPUT_MSG,
        }

    print("[Guardrails] OUTPUT ALLOWED")

    return {
        "allowed": True,
        "text": response_text,
    }