import json
import logging
import importlib.util
import sys
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

logger = logging.getLogger(__name__)


class UnifiedAutoGenTeamConfig(
    FunctionBaseConfig,
    name="unified_autogen_team"
):
    # Kept for compatibility with existing NAT YAML.
    llm_name: LLMRef = Field(description="NVIDIA NIM LLM configured in NAT YAML")
    tool_names: list[str] = Field(default_factory=list)

    # Defaults for orchestration inputs expected by utility.inference.start_agenting_process.
    default_index_type: str = "hybrid"
    default_filter: str = ""
    default_explain_code: bool = False
    default_category: str = ""
    default_email: str = ""


@register_function(
    config_type=UnifiedAutoGenTeamConfig,
    framework_wrappers=[LLMFrameworkEnum.AUTOGEN]
)
async def unified_autogen_team(
    config: UnifiedAutoGenTeamConfig,
    builder: Builder
) -> AsyncIterator[FunctionInfo]:
    # Ensure Backend root is importable so `utility.*` works in NAT runtime.
    backend_root = Path(__file__).resolve().parents[2]
    backend_root_str = str(backend_root)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)

    # Preserve NAT component resolution side effects/validation.
    await builder.get_llm(
        config.llm_name,
        wrapper_type=LLMFrameworkEnum.AUTOGEN,
    )
    if config.tool_names:
        await builder.get_tools(
            config.tool_names,
            wrapper_type=LLMFrameworkEnum.AUTOGEN,
        )

    async def _workflow(user_input: str) -> str:
        try:
            try:
                from utility.inference import start_agenting_process
            except ModuleNotFoundError:
                # Fallback import by absolute file path for NAT runtimes
                # that don't include Backend root on PYTHONPATH.
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
            return json.dumps(result)

        except Exception as e:
            logger.exception("Unified NAT AutoGen workflow failed")
            return json.dumps({"error": f"Workflow error: {str(e)}"})

    yield FunctionInfo.from_fn(
        _workflow,
        description="Run Unified AutoGen workflow through NeMo Agent Toolkit."
    )