"""
NVIDIA NeMo Reranker — re-scores Zilliz chunks by true relevance.
Sits between vector search and LLM in the RAG pipeline.
"""
import os
from dotenv import load_dotenv

load_dotenv("unified.env")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
RERANKER_MODEL = os.getenv("NVIDIA_RERANKER_MODEL", "nvidia/llama-nemotron-rerank-1b-v2")
RERANKER_TOP_N = int(os.getenv("RERANKER_TOP_N", "3"))
ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "true").strip().lower() == "true"


def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Takes the raw Zilliz chunks and reranks them by true relevance.

    Input chunks shape (from search_pdf_chunks_zilliz):
        [{"sourcepage": "file.pdf", "content": "chunk text"}, ...]

    Returns same shape, reranked and trimmed to RERANKER_TOP_N.
    """
    # If disabled or no chunks — return as is
    if not ENABLE_RERANKER or not chunks or not query.strip():
        return chunks[:RERANKER_TOP_N]

    try:
        from llama_index.postprocessor.nvidia_rerank import NVIDIARerank
        from llama_index.core.schema import NodeWithScore, TextNode

        # Convert your chunks to LlamaIndex nodes
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

        # Initialize reranker
        reranker = NVIDIARerank(
            model=RERANKER_MODEL,
            api_key=NVIDIA_API_KEY,
            top_n=RERANKER_TOP_N,
        )

        # Rerank
        reranked_nodes = reranker.postprocess_nodes(nodes, query_str=query)

        # Convert back to your chunk shape
        reranked_chunks = [
            {
                "content": node.node.text,
                "sourcepage": node.node.metadata.get("sourcepage", ""),
                "rerank_score": round(node.score, 4) if node.score else 0.0,
            }
            for node in reranked_nodes
        ]

        print(f"[Reranker] {len(chunks)} chunks -> {len(reranked_chunks)} after reranking")
        return reranked_chunks

    except Exception as e:
        print(f"[Reranker] Failed, using original order: {e}")
        return chunks[:RERANKER_TOP_N]
