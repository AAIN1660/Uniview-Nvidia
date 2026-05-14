"""
NVIDIA NeMo Reranker — re-scores Zilliz chunks by true relevance.
Sits between vector search and LLM in the RAG pipeline.

Diagnostics: this module ALWAYS prints a single ``[Reranker] ...`` line on
every call so you can verify from logs whether re-ranking actually fired
(disabled / skipped / succeeded / failed). The PowerShell unified.env loader
leaves quotes in place, so we ``.strip().strip('"').strip("'")`` defensively.
"""
import os
from dotenv import load_dotenv

load_dotenv("unified.env")


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

# One-time announce at import — visible in nat serve startup logs
print(
    f"[Reranker] module loaded — ENABLE_RERANKER={ENABLE_RERANKER}, "
    f"model={RERANKER_MODEL}, top_n={RERANKER_TOP_N}, key_set={bool(NVIDIA_API_KEY)}"
)


def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Re-rank vector chunks against the user query using NVIDIA NIM.

    Input chunks shape (from search_pdf_chunks_zilliz or zilliz_client.search_chunks):
        [{"sourcepage": "file.pdf", "content": "chunk text"}, ...]

    Returns same shape, reranked and trimmed to RERANKER_TOP_N.
    """
    n_in = len(chunks)
    if not ENABLE_RERANKER:
        print(f"[Reranker] DISABLED (ENABLE_RERANKER=false); returning top-{RERANKER_TOP_N} of {n_in}")
        return chunks[:RERANKER_TOP_N]
    if not chunks:
        print("[Reranker] SKIP — no chunks")
        return []
    if not query.strip():
        print(f"[Reranker] SKIP — empty query; returning top-{RERANKER_TOP_N} of {n_in}")
        return chunks[:RERANKER_TOP_N]

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

        scores_preview = [c.get("rerank_score") for c in reranked_chunks]
        print(
            f"[Reranker] OK — {n_in} -> {len(reranked_chunks)} chunks "
            f"(model={RERANKER_MODEL}, scores={scores_preview})"
        )
        return reranked_chunks

    except Exception as e:
        print(f"[Reranker] FAILED — falling back to retrieval order ({type(e).__name__}: {e})")
        return chunks[:RERANKER_TOP_N]
