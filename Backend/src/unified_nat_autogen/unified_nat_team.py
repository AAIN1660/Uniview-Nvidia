import json
import logging
import importlib.util
import sys
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

logger = logging.getLogger(__name__)


class UnifiedNatTeamConfig(
    FunctionBaseConfig,
    name="unified_nat_team",
):
    llm_name: LLMRef = Field(description="NVIDIA NIM LLM (reserved for NAT YAML; orchestration uses NIM via inference env)")
    tool_names: list[str] = Field(default_factory=list)

    default_index_type: str = "hybrid"
    default_filter: str = ""
    default_explain_code: bool = False
    default_category: str = ""
    default_email: str = ""


@register_function(
    config_type=UnifiedNatTeamConfig,
    framework_wrappers=None,
)
async def unified_nat_team(
    config: UnifiedNatTeamConfig,
    builder: Builder,
) -> AsyncIterator[FunctionInfo]:
    del builder  # Orchestration uses utility.unified_nat_orchestrator (OpenAI-compatible NIM client).

    backend_root = Path(__file__).resolve().parents[2]
    backend_root_str = str(backend_root)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)

    async def _workflow(user_input: str) -> str:
        try:
            try:
                from utility.inference import start_agenting_process
            except ModuleNotFoundError:
                inference_path = backend_root / "utility" / "inference.py"
                spec = importlib.util.spec_from_file_location(
                    "utility.inference", inference_path
                )
                if spec is None or spec.loader is None:
                    raise
                inference_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(inference_module)
                start_agenting_process = getattr(
                    inference_module, "start_agenting_process"
                )

            payload = {}
            if isinstance(user_input, str):
                stripped = user_input.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        payload = json.loads(stripped)
                    except json.JSONDecodeError:
                        payload = {}

            query = (
                payload.get("query")
                or payload.get("question")
                or (user_input if isinstance(user_input, str) else "")
            )
            index_type = payload.get("index_type", config.default_index_type)
            filter_value = payload.get("filter", config.default_filter)
            explain_code = payload.get("explain_code", config.default_explain_code)
            category = payload.get("category", config.default_category)
            email = payload.get("email", config.default_email)

            if not query:
                return json.dumps(
                    {
                        "error": "Missing query/question in workflow input.",
                        "hint": (
                            "Pass plain text or JSON with key 'query' (or 'question')."
                        ),
                    }
                )

            result = await start_agenting_process(
                query=query,
                index_type=index_type,
                filter=filter_value,
                explain_code=explain_code,
                category=category,
                email=email,
            )
            if isinstance(result, dict):
                try:
                    from utility.latency_report import print_nat_workflow_latency_table

                    print_nat_workflow_latency_table(result)
                except Exception:
                    logger.exception("Latency table logging failed")

            return json.dumps(result)

        except Exception as e:
            logger.exception("Unified NAT workflow failed")
            return json.dumps({"error": f"Workflow error: {str(e)}"})

    yield FunctionInfo.from_fn(
        _workflow,
        description="Run unified multi-agent workflow (NAT-native orchestration, same prompts and agent steps).",
    )
