"""
NAT-native multi-agent orchestration (OpenAI-compatible NIM calls).
Mirrors the former AutoGen GroupChat + state_transition flow in utility/inference.py.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from typing import Any

from utility.agent_prompts import (
    CRITIC_AGENT_PROMPT,
    INSIGHT_GENERATOR_PROMPT,
    LLM_ANSWER_MAKER_PROMPT,
    QUERY_TRANSFORMER_PROMPT,
    SELECTOR_AGENT_PROMPT,
    SQL_EXECUTOR_PROMPT,
    SQL_TOOL_PROMPT,
    routing_agent_prompt,
    sql_execution_critic_prompt,
    sql_generator_prompt,
)
from utility.helper import get_sql_engine
from utility.nim_chat_client import chat_completion, chat_completion_raw_messages


def _fmt_schema(all_table_schemas: Any) -> str:
    if isinstance(all_table_schemas, dict):
        return json.dumps(all_table_schemas, indent=2, ensure_ascii=False)
    return str(all_table_schemas or "")


def _log_message(
    transcript: list[dict[str, Any]], name: str, content: str, role: str = "assistant"
) -> None:
    transcript.append({"name": name, "role": role, "content": content})


def execute_sql_tool(query: str | None, connection_string: str) -> str:
    """Same behavior as legacy Sql_tool execute_query.

    Uses the shared pooled engine from ``utility.helper.get_sql_engine`` so
    the connection pool is reused across the up-to-8 SQL critic rounds and
    across requests, instead of spinning up a new engine per call.
    """
    import pandas as pd

    if not query:
        return "An error occurred while execusting the query: empty query"
    try:
        engine = get_sql_engine(connection_string)
        df = pd.read_sql(query, engine)
        return df.to_json(orient="records")
    except Exception as e:
        return f"An error occurred while execusting the query:{e}"


class _ChatHistoryShim:
    """Minimal stand-in for AutoGen chat_history used by agent_output_jsonparser."""

    def __init__(self, chat_history: list[dict[str, Any]]) -> None:
        self.chat_history = chat_history


def _detect_analysis_type_from_text(content: str) -> str:
    c = content or ""
    if "Both-dependent" in c:
        return "Both-dependent"
    if "Both-independent" in c:
        return "Both-independent"
    if "Semantic-based" in c:
        return "Semantic-based"
    if "SQL-based" in c:
        return "SQL-based"
    return ""


async def run_unified_nat_orchestration(
    *,
    query: str,
    index_type: str,
    filter_value: str,
    explain_code: bool,
    category: str,
    email: str,
    all_table_schemas: Any,
    connection_string: str,
) -> dict[str, Any]:
    """
    End-to-end unified workflow without AutoGen.
    Imports inference helpers lazily to avoid import cycles at module load.
    """
    from utility import inference as inf

    start = time.time()
    agent_latency: dict[str, float] = {}
    transcript: list[dict[str, Any]] = []
    total_tokens = 0

    schema_text = _fmt_schema(all_table_schemas)

    inf.extract_data(query, index_type, filter_value, explain_code, category)

    # --- Routing (replaces user_proxy -> routing_agent) ---
    routing_sys = routing_agent_prompt(schema_text)
    routing_user = f""""question": {query}"""
    routing_content, tok = await chat_completion(
        "routing_agent", routing_sys, routing_user, agent_latency
    )
    total_tokens += tok
    _log_message(transcript, "routing_agent", routing_content)

    routing_parsed = inf.parse_agent_content_json(routing_content)
    analysis_type = routing_parsed.get("analysis_type") or _detect_analysis_type_from_text(
        routing_content
    )

    sql_query = ""
    sql_explanation: str = ""
    python_code = None
    python_code_explanation = None
    data_points: Any = "{}"
    analysis_type_out = analysis_type
    sql_answer = ""
    llm_answer = ""
    final_answer: Any = ""
    formated_final_answer: Any = ""

    # Track semantic branch fields updated post-SQL (Both-* flows)
    selector_context: dict[str, Any] = {
        "initial_question": query,
        "analysis_type": analysis_type_out,
        "sql_query": "",
        "sql_answer": "",
        "updated_question": query,
    }

    async def run_sql_chain(
        initial_feedback: str | None = None,
    ) -> tuple[str, str, str, bool, str | None]:
        """Returns (insight_content, sql_query, sql_tool_output, semantic_early_exit, critic_snapshot)."""
        nonlocal total_tokens
        feedback_hint = initial_feedback or ""
        last_sql_tool_output = ""
        accumulated_sql_query = ""
        semantic_early_exit = False
        critic_snapshot: str | None = None
        sg_content = ""

        max_sql_rounds = 8
        for round_idx in range(max_sql_rounds):
            gen_user_parts = [
                f"User question: {query}",
                f"Routing JSON: {json.dumps(routing_parsed, ensure_ascii=False)}",
            ]
            if feedback_hint:
                gen_user_parts.append(f"Revision feedback from Sql_Execution_Critic / Sql_Generator loop:\n{feedback_hint}")
            gen_user = "\n\n".join(gen_user_parts)

            sg_content, tok = await chat_completion(
                "Sql_Generator",
                sql_generator_prompt(schema_text),
                gen_user,
                agent_latency,
            )
            total_tokens += tok
            _log_message(transcript, "Sql_Generator", sg_content)

            sg_parsed = inf.parse_agent_content_json(sg_content)
            q = sg_parsed.get("sql_query")
            accumulated_sql_query = q if isinstance(q, str) else (accumulated_sql_query or "")

            # Sql_Executor (LLM step preserved)
            se_user = (
                f"Sql_Generator output:\n{sg_content}\n\n"
                f"Validate and confirm execution path for SQL against the user question:\n{query}"
            )
            se_content, tok = await chat_completion(
                "Sql_Executor", SQL_EXECUTOR_PROMPT, se_user, agent_latency
            )
            total_tokens += tok
            _log_message(transcript, "Sql_Executor", se_content)

            # Sql_tool prompt-only agent - execution happens deterministically
            st_user = (
                f"Sql_Executor output:\n{se_content}\n\n"
                f"Extract sql_query from Sql_Generator JSON if present; executable query:\n{q}"
            )
            st_content, tok = await chat_completion(
                "Sql_tool", SQL_TOOL_PROMPT, st_user, agent_latency
            )
            total_tokens += tok
            active_query = q if isinstance(q, str) and q.strip() else None
            if active_query is None:
                tool_out = "An error occurred while execusting the query: no sql_query from Sql_Generator"
            else:
                tool_out = await asyncio.to_thread(
                    execute_sql_tool, active_query, connection_string
                )

            last_sql_tool_output = tool_out
            _log_message(transcript, "Sql_tool", tool_out)

            critic_user = (
                f"initial_question: {query}\n\n"
                f"Sql_Generator:\n{sg_content}\n\n"
                f"Sql_tool output:\n{tool_out}\n"
            )
            critic_content, tok = await chat_completion(
                "Sql_Execution_Critic",
                sql_execution_critic_prompt(schema_text),
                critic_user,
                agent_latency,
            )
            total_tokens += tok
            _log_message(transcript, "Sql_Execution_Critic", critic_content)

            critic_info = inf.parse_agent_content_json(critic_content)
            evaluation = critic_info.get("sql_critic_evaluation")
            feedback = str(critic_info.get("feedback") or "").lower()
            next_step = str(critic_info.get("next_step") or "").lower()

            happy = "happy with the result" in critic_content.lower()
            success_exec = (
                tool_out
                and tool_out.lower() not in ("none", "[]")
                and "An error occurred while execusting the query" not in tool_out
            )

            if happy or evaluation == 1 or success_exec:
                break

            if "semantic" in feedback or "semantic" in next_step:
                semantic_early_exit = True
                critic_snapshot = critic_content
                break

            feedback_hint = critic_content
            if round_idx == max_sql_rounds - 1:
                break

        if semantic_early_exit:
            return "", accumulated_sql_query or "", last_sql_tool_output, True, critic_snapshot

        # Insight_Generator
        insight_user = (
            f"User question: {query}\n"
            f"Routing:\n{routing_content}\n\n"
            f"Sql_Generator:\n{sg_content}\n\n"
            f"Sql_tool output:\n{last_sql_tool_output}\n"
        )
        insight_content, tok = await chat_completion(
            "Insight_Generator",
            INSIGHT_GENERATOR_PROMPT,
            insight_user,
            agent_latency,
        )
        total_tokens += tok
        _log_message(transcript, "Insight_Generator", insight_content)
        return insight_content, accumulated_sql_query or "", last_sql_tool_output, False, None

    async def run_semantic_chain(
        *,
        selector_extra: str,
        updated_question_override: str | None,
        sql_q: str,
        sql_ans: str,
    ) -> str:
        nonlocal total_tokens, data_points
        sel_user = (
            f"{selector_extra}\n\n"
            f"Routing JSON:\n{json.dumps(routing_parsed, ensure_ascii=False)}\n\n"
            f"Carry forward:\n{json.dumps(selector_context, ensure_ascii=False)}\n\n"
            f"If updated_question_override is set, use it for retrieval:\n{updated_question_override or ''}"
        )
        sel_content, tok = await chat_completion(
            "Selector_agent", SELECTOR_AGENT_PROMPT, sel_user, agent_latency
        )
        total_tokens += tok
        _log_message(transcript, "Selector_agent", sel_content)

        sel_parsed = inf.parse_agent_content_json(sel_content)
        q_ret = (
            updated_question_override
            or sel_parsed.get("updated_question")
            or sel_parsed.get("question")
            or query
        )

        ctx = await inf.extract_context(question=q_ret)
        data_points = json.dumps(ctx)
        _log_message(transcript, "retriever", data_points)

        lam_user = json.dumps(
            {"question": q_ret, "context": ctx, "analysis_type": analysis_type_out},
            ensure_ascii=False,
        )
        lam_messages = [
            {"role": "system", "content": LLM_ANSWER_MAKER_PROMPT},
            {"role": "user", "content": lam_user},
        ]
        lam_content, tok = await chat_completion_raw_messages(
            "llm_answer_maker", lam_messages, agent_latency
        )
        total_tokens += tok
        _log_message(transcript, "llm_answer_maker", lam_content)

        critic_rounds = 8
        last_lam = lam_content
        for _ in range(critic_rounds):
            crit_user = json.dumps(
                {"question": q_ret, "llm_answer": last_lam, "context": ctx},
                ensure_ascii=False,
            )
            crit_messages = [
                {"role": "system", "content": CRITIC_AGENT_PROMPT},
                {"role": "user", "content": crit_user},
            ]
            crit_content, tok = await chat_completion_raw_messages(
                "critic_agent", crit_messages, agent_latency
            )
            total_tokens += tok
            _log_message(transcript, "critic_agent", crit_content)

            if "Happy with the answer" in crit_content:
                return last_lam

            cp = inf.parse_agent_content_json(crit_content)
            fq = cp.get("feedback_query")
            if fq in (None, "", "None") or str(fq).lower() == "none":
                return last_lam

            sel_user2 = (
                f"Critic requested more context. feedback_query:\n{fq}\n\n"
                f"Original selector payload:\n{sel_content}"
            )
            sel_content2, tok = await chat_completion(
                "Selector_agent", SELECTOR_AGENT_PROMPT, sel_user2, agent_latency
            )
            total_tokens += tok
            _log_message(transcript, "Selector_agent", sel_content2)

            ctx = await inf.extract_context(question=str(fq))
            data_points = json.dumps(ctx)
            _log_message(transcript, "retriever", data_points)

            lam_user2 = json.dumps(
                {"question": fq, "context": ctx, "analysis_type": analysis_type_out},
                ensure_ascii=False,
            )
            lam_messages2 = [
                {"role": "system", "content": LLM_ANSWER_MAKER_PROMPT},
                {"role": "user", "content": lam_user2},
            ]
            last_lam, tok = await chat_completion_raw_messages(
                "llm_answer_maker", lam_messages2, agent_latency
            )
            total_tokens += tok
            _log_message(transcript, "llm_answer_maker", last_lam)

        return last_lam

    # --- Branch by routing ---
    if analysis_type == "Semantic-based":
        llm_answer = await run_semantic_chain(
            selector_extra="Semantic-only path: set updated_question to the user question.",
            updated_question_override=query,
            sql_q="",
            sql_ans="",
        )
        final_answer = {"llm_answer": llm_answer, "sql_answer": ""}
    elif analysis_type in ("SQL-based", "Both-dependent", "Both-independent"):
        sem_early = False
        critic_snap: str | None = None
        insight_content, sql_query, sql_tool_out, sem_early, critic_snap = await run_sql_chain()
        selector_context["sql_query"] = sql_query

        for msg in reversed(transcript):
            if msg.get("name") == "Sql_Generator":
                sg_parsed = inf.parse_agent_content_json(msg.get("content") or "")
                sql_explanation = sg_parsed.get("sql_explanation") or ""
                break

        _insight = inf.parse_agent_content_json(insight_content) if insight_content.strip() else {}
        python_code = _insight.get("python_code")
        python_code_explanation = _insight.get("code_explaination") or _insight.get(
            "code_explanation"
        )
        insight_text = (
            _insight.get("Inference")
            or _insight.get("llm_answer")
            or _insight.get("insight")
            or ""
        )

        sql_answer = ""
        if analysis_type == "SQL-based":
            final_answer = {
                "sql_answer": _insight.get("sql_answer"),
                "llm_answer": insight_text,
            }
        else:
            sql_answer = _insight.get("sql_answer") or ""
            selector_context["sql_answer"] = sql_answer

        need_semantic = analysis_type in ("Both-dependent", "Both-independent") or (
            "Both" in insight_content
        )
        # SQL-only path can still require semantic refinement if Insight echoes "Both"
        if analysis_type == "SQL-based":
            need_semantic = "Both" in insight_content

        if need_semantic:
            if sem_early and critic_snap:
                qt_user = (
                    f"Sql_Execution_Critic (semantic handoff):\n{critic_snap}\n\n"
                    f"Initial question:\n{query}\n"
                )
            else:
                qt_user = (
                    f"Insight_Generator output:\n{insight_content}\n\n"
                    f"Initial question:\n{query}\n"
                )
            qt_content, tok = await chat_completion(
                "query_transformer",
                QUERY_TRANSFORMER_PROMPT,
                qt_user,
                agent_latency,
            )
            total_tokens += tok
            _log_message(transcript, "query_transformer", qt_content)

            qt_parsed = inf.parse_agent_content_json(qt_content)
            uq = qt_parsed.get("updated_question") or query
            selector_context.update(qt_parsed)

            llm_answer = await run_semantic_chain(
                selector_extra="Both SQL + semantic path after SQL insights.",
                updated_question_override=uq,
                sql_q=sql_query,
                sql_ans=sql_answer,
            )

            final_answer = {"sql_answer": sql_answer, "llm_answer": llm_answer}

            if analysis_type in ("Both-dependent", "Both-independent"):
                if (
                    not isinstance(final_answer, dict)
                    or not str(final_answer.get("sql_answer") or "").strip()
                    and not str(final_answer.get("llm_answer") or "").strip()
                ):
                    fb = inf.build_generic_sql_fallback_answer(transcript)
                    if fb.get("sql_answer") or fb.get("llm_answer"):
                        final_answer = fb
        elif analysis_type == "SQL-based":
            # Mirror fallback usage for blank Insight outputs
            if (
                not isinstance(final_answer, dict)
                or (
                    not str(final_answer.get("sql_answer") or "").strip()
                    and not str(final_answer.get("llm_answer") or "").strip()
                )
            ):
                fb = inf.build_generic_sql_fallback_answer(transcript)
                if fb.get("sql_answer") or fb.get("llm_answer"):
                    final_answer = fb
    else:
        # Unknown routing - attempt SQL then semantic
        insight_content, sql_query, _, _, _ = await run_sql_chain()
        llm_answer = await run_semantic_chain(
            selector_extra="Fallback: routing classification unclear; run semantic enrichment.",
            updated_question_override=query,
            sql_q=sql_query,
            sql_ans="",
        )
        _insight = inf.parse_agent_content_json(insight_content)
        final_answer = {
            "sql_answer": _insight.get("sql_answer") or "",
            "llm_answer": llm_answer or insight_content,
        }

    # --- Format final answer (same helper as legacy stack) ---
    formated_answer = await asyncio.to_thread(inf.formating_final_answer, final_answer)
    formated_final_answer = json.loads(
        formated_answer.replace("```json", "").replace("```", "").strip()
    )

    try:
        if isinstance(data_points, str) and data_points.strip():
            parsed_data_points = json.loads(data_points)
        elif isinstance(data_points, dict):
            parsed_data_points = data_points
        else:
            parsed_data_points = {}
    except Exception as e:
        print("Warning: unable to parse data_points:", e)
        parsed_data_points = {}

    thoughts_list = []
    for msg in transcript:
        name = msg.get("name")
        content = msg.get("content")
        role = msg.get("role")
        thoughts_list.append(
            '<div style="border: 1px solid #ccc; padding: 20px; border-radius: 5px; width: fit-content;">'
            f"<h2>{name}</h2><br /><h4>Role: {role}</h4><br />{content}</div>"
        )
    thoughts = "\n <br/> <br />".join(thoughts_list)

    end = time.time()

    response: dict[str, Any] = {
        "data_points": parsed_data_points,
        "answer": formated_final_answer,
        "thoughts": thoughts,
        "sql_query": sql_query,
        "token_usage": total_tokens,
        "agent_latencies": {k: round(v, 3) for k, v in agent_latency.items()},
        "orchestration_total_latency_sec": round(end - start, 3),
    }

    if python_code:
        response["python_code"] = python_code
        generated_plot = await asyncio.to_thread(inf.plot_to_base64, python_code)
        if generated_plot:
            response["plot_base64"] = "data:image/png;base64," + generated_plot
        else:
            print("Plot generation failed; continuing without plot_base64.")
    if explain_code and sql_explanation:
        response["sql_explanation"] = sql_explanation
        if python_code_explanation:
            response["python_code_explanation"] = python_code_explanation

    cache_path = os.path.join(os.getcwd(), ".cache")
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path)
        print(f"Deleted directory: {cache_path}")

    return response
