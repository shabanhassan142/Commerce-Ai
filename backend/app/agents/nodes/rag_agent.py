"""
app/agents/nodes/rag_agent.py

RAG Agent node — answers policy and FAQ questions using FAISS knowledge base.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.agents.state import CommerceFlowState
from app.agents.tools.rag_tools import RAG_TOOLS
from app.core.logging import get_logger
from app.rag.retriever import get_retriever

logger = get_logger(__name__)


def rag_agent_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    RAG Agent: perform semantic search and populate retrieved_documents + tool_results.
    Also extracts citations from high-scoring results.
    """
    logger.info(f"RAG agent processing conversation {state['conversation_id']}")

    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if not last_human:
        return {**state, "tool_results": [], "retrieved_documents": [], "citations": []}

    query = last_human.content
    tool_results = []
    citations = []

    try:
        # Direct FAISS retrieval (no LLM needed for this step)
        retriever = get_retriever()
        results = retriever.search(query, top_k=5, score_threshold=0.3)

        retrieved_documents = results

        # Build citation list from high-confidence results
        for i, r in enumerate(results):
            if r["score"] >= 0.5:
                source = r["metadata"].get("source", "knowledge base")
                citations.append({
                    "index": i + 1,
                    "source": source,
                    "score": round(r["score"], 3),
                    "text_preview": r["text"][:150],
                })

        # Format as tool result
        if results:
            formatted = RAG_TOOLS[0].invoke({"query": query, "top_k": 5})
            tool_results.append({
                "tool": "search_knowledge_base",
                "input": {"query": query},
                "output": formatted,
            })
        else:
            tool_results.append({
                "tool": "search_knowledge_base",
                "input": {"query": query},
                "output": "No relevant information found in the knowledge base.",
            })

    except Exception as e:
        logger.error(f"RAG agent failed: {e}", exc_info=True)
        tool_results.append({
            "tool": "search_knowledge_base",
            "input": {"query": query},
            "output": f"Knowledge base search temporarily unavailable: {e}",
        })
        retrieved_documents = []

    return {
        **state,
        "tool_results": tool_results,
        "retrieved_documents": retrieved_documents,
        "citations": citations,
        "selected_agent": "rag_agent",
    }
