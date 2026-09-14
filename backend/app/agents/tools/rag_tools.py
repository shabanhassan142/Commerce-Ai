"""
app/agents/tools/rag_tools.py

Tools for knowledge base retrieval using FAISS.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.core.logging import get_logger
from app.rag.retriever import get_retriever

logger = get_logger(__name__)


@tool
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """
    Search the knowledge base for answers to policy, FAQ, and general questions.
    Use for questions about: return policies, shipping info, payments, FAQs,
    how things work, company policies, or anything not answered by order/product tools.

    Args:
        query: The natural language question to search for
        top_k: Number of relevant chunks to retrieve (default 4)

    Returns:
        Relevant text passages from the knowledge base with source labels
    """
    try:
        retriever = get_retriever()
        results = retriever.search(query, top_k=top_k, score_threshold=0.3)

        if not results:
            return "No relevant information found in the knowledge base for this query."

        lines = [f"Found {len(results)} relevant knowledge base passages:\n"]
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "unknown")
            score = r["score"]
            text = r["text"]
            lines.append(f"[{i}] Source: {source} (relevance: {score:.2f})")
            lines.append(f"    {text}\n")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return f"Knowledge base search error: {str(e)}"


RAG_TOOLS = [search_knowledge_base]
