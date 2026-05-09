import os
import inspect
from typing import Any, Dict
from urllib.parse import urlparse

def _clean_env(value: str | None, default: str | None = None) -> str | None:
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


def _normalize_base_url(base_url: str | None) -> str:
    """
    Normalize NVIDIA base URL so HTTP clients always receive a valid URL.
    """
    value = _clean_env(base_url, "https://integrate.api.nvidia.com/v1") or ""
    parsed = urlparse(value)

    # Accept values like integrate.api.nvidia.com/v1 and normalize to https.
    if not parsed.scheme:
        value = f"https://{value.lstrip('/')}"
        parsed = urlparse(value)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            "NVIDIA_BASE_URL must be a valid http(s) URL, e.g. "
            "https://integrate.api.nvidia.com/v1"
        )

    return value


def get_nemo_autogen_llm_config() -> Dict[str, Any]:
    """
    Returns an AutoGen-compatible LLM configuration backed by NVIDIA NeMo Agent Toolkit.

    This keeps AutoGen orchestration unchanged.
    It only replaces the model service/client layer with the NeMo Agent Toolkit
    AutoGen NIM integration.
    """
    nvidia_base_url = _normalize_base_url(os.getenv("NVIDIA_BASE_URL"))
    nvidia_model = _clean_env(
        os.getenv("NVIDIA_MODEL"), "meta/llama-3.3-70b-instruct"
    )
    nvidia_api_key = _clean_env(os.getenv("NVIDIA_API_KEY"), "")

    if not nvidia_api_key:
        raise ValueError("NVIDIA_API_KEY is required in unified.env")

    try:
        from nat.plugins.autogen.llm import nim_autogen
    except Exception as exc:
        raise ImportError(
            "NeMo Agent Toolkit AutoGen integration is not available. "
            "Install it using: pip install nvidia-nat"
        ) from exc

    # Keep NIM as backend in all cases.
    base_config = {
        "config_list": [
            {
                "model": nvidia_model,
                "api_type": "openai",
                "base_url": nvidia_base_url,
                "api_key": nvidia_api_key,
            }
        ],
        "cache_seed": None,
        "temperature": 0.1,
        "timeout": 120,
    }

    # NAT's nim_autogen signature varies by version.
    # Older docs/examples accept (model, api_key, base_url), but your installed
    # build expects (llm_config, _builder) and is not directly usable here.
    try:
        params = inspect.signature(nim_autogen).parameters
        supports_direct_kwargs = all(
            key in params for key in ("model", "api_key", "base_url")
        )
    except (TypeError, ValueError):
        supports_direct_kwargs = False

    if not supports_direct_kwargs:
        return base_config

    nemo_client = nim_autogen(
        model=nvidia_model,
        api_key=nvidia_api_key,
        base_url=nvidia_base_url,
    )

    base_config["config_list"][0]["client"] = nemo_client
    return base_config


def get_direct_nvidia_llm_config() -> Dict[str, Any]:
    """
    Emergency fallback only. If NAT client wiring is not compatible
    with the installed AutoGen version.
    """
    nvidia_base_url = _normalize_base_url(os.getenv("NVIDIA_BASE_URL"))
    nvidia_model = _clean_env(
        os.getenv("NVIDIA_MODEL"), "meta/llama-3.3-70b-instruct"
    )
    nvidia_api_key = _clean_env(os.getenv("NVIDIA_API_KEY"), "")

    if not nvidia_api_key:
        raise ValueError("NVIDIA_API_KEY is required in unified.env")

    return {
        "config_list": [
            {
                "model": nvidia_model,
                "api_type": "openai",
                "base_url": nvidia_base_url,
                "api_key": nvidia_api_key,
            }
        ],
        "cache_seed": None,
        "temperature": 0.1,
        "timeout": 120,
    }