import os

from dotenv import load_dotenv

# Pull in the entire existing Azure implementation (including Azure embeddings),
# then override ONLY the Autogen chat/LLM configuration to use NVIDIA.
from utility.inference import *  # noqa: F401,F403

load_dotenv("unified.env")

NVIDIA_BASE_URL = (os.getenv("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1").strip()
NVIDIA_MODEL = (os.getenv("NVIDIA_MODEL") or "meta/llama-3.3-70b-instruct").strip()
NVIDIA_API_KEY = (os.getenv("NVIDIA_API_KEY") or "").strip()
if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY is required in unified.env")

# Override the Azure llm_config imported from utility.inference
llm_config = {
    "config_list": [
        {
            "model": NVIDIA_MODEL,
            "api_type": "openai",
            "base_url": NVIDIA_BASE_URL,
            "api_key": NVIDIA_API_KEY,
        }
    ],
    "cache_seed": None,
    "temperature": 0.1,
}

