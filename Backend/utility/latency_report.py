"""
Sequential end-to-end latency table (numbered steps that sum to total).
"""

from __future__ import annotations

import os
from typing import Any

from utility.latency_trace import LatencyTrace


def _excel_export_enabled() -> bool:
    v = os.getenv("LATENCY_TABLE_EXCEL", "1").strip().lower()
    return v not in ("0", "false", "no", "off")

# Chronological API phases before NAT HTTP call
_PRE_NAT_PHASES: list[tuple[str, str]] = [
    ("check_balance_sec", "Check balance"),
    ("get_all_categories_sec", "Load categories"),
    ("qa_exact_lookup_sec", "QA exact-match lookup"),
    ("qa_similarity_lookup_sec", "QA similarity lookup"),
    ("input_guardrail_sec", "Input guardrail"),
]

# After NAT returns
_POST_NAT_PHASES: list[tuple[str, str]] = [
    ("nat_response_parse_sec", "Parse NAT JSON response"),
    ("output_guardrail_sec", "Output guardrail"),
    ("process_query_update_sec", "Save query and update credits"),
]


def _flt(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), 3)
    except (TypeError, ValueError):
        return None


def _add_phases(trace: LatencyTrace, service_latencies: dict[str, Any], phases: list[tuple[str, str]]) -> None:
    for key, label in phases:
        sec = _flt(service_latencies.get(key))
        if sec is not None and sec > 0:
            trace.record(label, sec)


def build_e2e_latency_steps(
    service_latencies: dict[str, Any] | None,
    nat_metadata: dict[str, Any] | None,
    *,
    total_sec: float | None = None,
) -> list[dict[str, Any]]:
    """Merge FastAPI phases + NAT ``latency_steps`` in request order; close gap vs wall clock."""
    trace = LatencyTrace()
    sl = service_latencies or {}
    nm = nat_metadata or {}

    _add_phases(trace, sl, _PRE_NAT_PHASES)

    nat_steps: list[dict[str, Any]] = []
    if isinstance(nm.get("latency_steps"), list) and nm["latency_steps"]:
        nat_steps = list(nm["latency_steps"])

    if nat_steps:
        trace.extend(nat_steps)
        transport = _flt(sl.get("nat_transport_overhead_sec"))
        if transport is None:
            transport = _flt(nm.get("nat_transport_overhead_sec"))
        if transport is not None and transport > 0:
            trace.record("NAT HTTP client + serve wrapper", transport)
    else:
        nat_sec = _flt(sl.get("nat_workflow_sec")) or _flt(nm.get("latency_sec"))
        if nat_sec is not None and nat_sec > 0:
            trace.record("NAT workflow (not step-traced)", nat_sec)

    _add_phases(trace, sl, _POST_NAT_PHASES)

    total_f = _flt(total_sec)
    if total_f is not None:
        trace.append_gap_if_needed(total_f, label="API overhead (JSON, routing, misc)")
    return trace.to_list()


def format_latency_table_tsv(
    steps: list[dict[str, Any]],
    total_sec: float | None,
    *,
    title: str = "End-to-end latency",
) -> str:
    """Tab-separated rows for paste into Excel (one row per line, columns split on tabs)."""

    def _cell(text: str) -> str:
        return str(text).replace("\t", " ").replace("\r", " ").replace("\n", " ")

    total_f = _flt(total_sec)
    step_sum = round(sum(_flt(s.get("sec")) or 0 for s in steps), 3)
    rows: list[str] = [
        "\t".join(["title", _cell(title)]),
        "\t".join(["step", "label", "sec", "pct"]),
    ]
    for s in steps:
        n = s.get("step", "")
        lab = _cell(s.get("label", ""))
        sec = _flt(s.get("sec"))
        sec_s = "" if sec is None else f"{sec:.3f}"
        pct_s = ""
        if sec is not None and total_f and total_f > 0:
            pct_s = f"{100.0 * sec / total_f:.1f}"
        rows.append("\t".join([str(n), lab, sec_s, pct_s]))

    rows.append("\t".join(["", "SUM of steps", f"{step_sum:.3f}", ""]))
    if total_f is not None:
        rows.append("\t".join(["", "TOTAL (wall clock)", f"{total_f:.3f}", "100.0"]))
        gap = round(total_f - step_sum, 3)
        if abs(gap) > 0.01:
            rows.append("\t".join(["", "Untracked gap (should be ~0)", f"{gap:.3f}", ""]))
    return "\n".join(rows)


def print_latency_table_for_excel(
    steps: list[dict[str, Any]],
    total_sec: float | None,
    *,
    title: str = "End-to-end latency",
) -> None:
    """Print TSV block to copy from terminal into Excel."""
    tsv = format_latency_table_tsv(steps, total_sec, title=title)
    print(
        "\n".join(
            [
                "",
                "=" * 72,
                "EXCEL PASTE - select all lines between START and END, copy, paste into Excel",
                "START",
                tsv,
                "END",
                "=" * 72,
                "",
            ]
        ),
        flush=True,
    )


def print_sequential_latency_table(
    steps: list[dict[str, Any]],
    total_sec: float | None,
    *,
    title: str = "End-to-end latency",
) -> None:
    """Plain numbered steps 1..N; sum of steps should match total_sec."""
    label_w, sec_w, pct_w = 54, 10, 8
    total_f = _flt(total_sec)
    step_sum = round(sum(_flt(s.get("sec")) or 0 for s in steps), 3)

    lines: list[str] = ["", "+" + "-" * (label_w + 2) + "+" + "-" * (sec_w + 2) + "+" + "-" * (pct_w + 2) + "+"]
    lines.append(f"| {title[:label_w]:<{label_w}} | {'sec':>{sec_w}} | {'%':>{pct_w}} |")
    lines.append("+" + "-" * (label_w + 2) + "+" + "-" * (sec_w + 2) + "+" + "-" * (pct_w + 2) + "+")

    for s in steps:
        n = s.get("step", "?")
        lab = f"{n}. {s.get('label', '')}"[:label_w].ljust(label_w)
        sec = _flt(s.get("sec"))
        sec_s = "" if sec is None else f"{sec:,.3f}"
        pct_s = ""
        if sec is not None and total_f and total_f > 0:
            pct_s = f"{100.0 * sec / total_f:5.1f}%"
        lines.append(f"| {lab} | {sec_s:>{sec_w}} | {pct_s:>{pct_w}} |")

    lines.append("+" + "-" * (label_w + 2) + "+" + "-" * (sec_w + 2) + "+" + "-" * (pct_w + 2) + "+")
    lines.append(f"| {'SUM of steps above':<{label_w}} | {step_sum:>{sec_w},.3f} | {'':>{pct_w}} |")
    if total_f is not None:
        lines.append(f"| {'TOTAL (wall clock)':<{label_w}} | {total_f:>{sec_w},.3f} | {'100.0%':>{pct_w}} |")
        gap = round(total_f - step_sum, 3)
        if abs(gap) > 0.01:
            lines.append(
                f"| {'Untracked gap (should be ~0)':<{label_w}} | {gap:>{sec_w},.3f} | {'':>{pct_w}} |"
            )
    lines.append("+" + "-" * (label_w + 2) + "+" + "-" * (sec_w + 2) + "+" + "-" * (pct_w + 2) + "+")
    lines.append("")
    print("\n".join(lines), flush=True)
    if _excel_export_enabled():
        print_latency_table_for_excel(steps, total_sec, title=title)


def print_generate_response_latency_table(
    service_latencies: dict[str, Any],
    total_sec: float | None,
    *,
    nat_metadata: dict[str, Any] | None = None,
    title: str = "End-to-end latency (/generate_response)",
) -> None:
    steps = build_e2e_latency_steps(service_latencies, nat_metadata, total_sec=total_sec)
    print_sequential_latency_table(steps, total_sec, title=title)


def print_nat_workflow_latency_table(orchestrator_payload: dict[str, Any]) -> None:
    steps = orchestrator_payload.get("latency_steps")
    if not isinstance(steps, list):
        steps = []
    total = _flt(orchestrator_payload.get("orchestration_total_latency_sec")) or _flt(
        sum(_flt(s.get("sec")) or 0 for s in steps)
    )
    trace = LatencyTrace.from_label_sec_pairs([])
    trace.extend(steps)
    if total is not None:
        trace.append_gap_if_needed(total, label="Orchestrator overhead")
    print_sequential_latency_table(
        trace.to_list(),
        total,
        title="NAT orchestrator (sequential steps)",
    )
