"""
NVIDIA NeMo Reranker — re-scores Zilliz chunks by true relevance.
Sits between vector search and LLM in the RAG pipeline.

Diagnostics: this module ALWAYS emits a bordered banner block on every call
matching the NAT agent log format (72-char dashes), so reranker activity
sits visually next to ``[retriever]`` / ``[llm_answer_maker]`` in the flow
and is trivially grep-able for ``NIM-RERANKER``. The PowerShell unified.env
loader leaves quotes in place, so we ``.strip().strip('"').strip("'")``
defensively.
"""
import os
import time
from dotenv import load_dotenv

load_dotenv("unified.env")


_BAR = "=" * 72  # use '=' so it visually stands out vs NAT's '-' separators


def _banner(status: str, lines: list[str]) -> None:
    """Print a high-visibility bordered block. Always flushes."""
    body = "\n".join(lines)
    print(
        f"\n{_BAR}\n"
        f">>> NIM-RERANKER :: {status} <<<\n"
        f"{_BAR}\n"
        f"{body}\n"
        f"{_BAR}\n",
        flush=True,
    )


def _clean(v, default=""):
    if v is None:
        return default
    return v.strip().strip('"').strip("'")


NVIDIA_API_KEY = _clean(os.getenv("NVIDIA_API_KEY"))
RERANKER_MODEL = _clean(os.getenv("NVIDIA_RERANKER_MODEL")) or "nvidia/llama-nemotron-rerank-1b-v2"
try:
    RERANKER_TOP_N = max(1, int(_clean(os.getenv("RERANKER_TOP_N")) or "3"))
except ValueError:
    RERANKER_TOP_N = 3
ENABLE_RERANKER = (_clean(os.getenv("ENABLE_RERANKER")) or "true").lower() == "true"


_banner(
    "MODULE LOADED",
    [
        f"ENABLE_RERANKER = {ENABLE_RERANKER}",
        f"model           = {RERANKER_MODEL}",
        f"top_n           = {RERANKER_TOP_N}",
        f"api_key_set     = {bool(NVIDIA_API_KEY)}",
        "(this banner prints once at nat serve startup; per-call banners follow)",
    ],
)


def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Re-rank vector chunks against the user query using NVIDIA NIM.

    Input chunks shape (from search_pdf_chunks_zilliz or zilliz_client.search_chunks):
        [{"sourcepage": "file.pdf", "content": "chunk text"}, ...]

    Returns same shape, reranked and trimmed to RERANKER_TOP_N.
    """
    n_in = len(chunks)
    query_preview = (query[:80] + "…") if query and len(query) > 80 else (query or "")

    if not ENABLE_RERANKER:
        _banner(
            "DISABLED (early return)",
            [
                "ENABLE_RERANKER=false in unified.env",
                f"input_chunks  = {n_in}",
                f"returning     = top-{RERANKER_TOP_N} from retrieval order",
            ],
        )
        return chunks[:RERANKER_TOP_N]

    if not chunks:
        _banner(
            "SKIP — no input chunks",
            ["upstream retriever returned 0 chunks; nothing to rerank"],
        )
        return []

    if not query.strip():
        _banner(
            "SKIP — empty query",
            [
                f"input_chunks  = {n_in}",
                f"returning     = top-{RERANKER_TOP_N} from retrieval order",
            ],
        )
        return chunks[:RERANKER_TOP_N]

    t0 = time.perf_counter()
    try:
        from llama_index.postprocessor.nvidia_rerank import NVIDIARerank
        from llama_index.core.schema import NodeWithScore, TextNode

        nodes = [
            NodeWithScore(
                node=TextNode(
                    text=c.get("content", ""),
                    metadata={"sourcepage": c.get("sourcepage", "")},
                ),
                score=1.0,
            )
            for c in chunks
        ]

        reranker = NVIDIARerank(
            model=RERANKER_MODEL,
            api_key=NVIDIA_API_KEY,
            top_n=RERANKER_TOP_N,
        )

        reranked_nodes = reranker.postprocess_nodes(nodes, query_str=query)

        reranked_chunks = [
            {
                "content": node.node.text,
                "sourcepage": node.node.metadata.get("sourcepage", ""),
                "rerank_score": round(node.score, 4) if node.score else 0.0,
            }
            for node in reranked_nodes
        ]

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        scores_preview = [c.get("rerank_score") for c in reranked_chunks]
        sources_preview = [c.get("sourcepage", "") for c in reranked_chunks]
        _banner(
            "OK — reranking applied",
            [
                f"query         = {query_preview}",
                f"model         = {RERANKER_MODEL}",
                f"input_chunks  = {n_in}  ->  output_chunks = {len(reranked_chunks)}",
                f"latency_ms    = {elapsed_ms}",
                f"top_scores    = {scores_preview}",
                f"top_sources   = {sources_preview}",
            ],
        )
        return reranked_chunks

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        _banner(
            "FAILED — falling back to retrieval order",
            [
                f"error_type    = {type(e).__name__}",
                f"error_message = {e}",
                f"latency_ms    = {elapsed_ms}",
                f"input_chunks  = {n_in}",
                f"returning     = top-{RERANKER_TOP_N} from retrieval order",
            ],
        )
        return chunks[:RERANKER_TOP_N]
