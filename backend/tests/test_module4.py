"""
tests/test_module4.py

Integration and unit tests for Module 4 — LangGraph Multi-Agent System.
Tests state, routing, tools, memory, RAG retrieval, and full Chat API.
"""

import asyncio
import pytest
from app.agents.state import initial_state
from app.agents.nodes.supervisor import _rule_based_routing
from app.agents.tools.order_tools import ORDER_TOOLS
from app.agents.tools.product_tools import PRODUCT_TOOLS
from app.agents.tools.refund_tools import REFUND_TOOLS
from app.agents.tools.rag_tools import RAG_TOOLS
from app.agents.tools.ticket_tools import TICKET_TOOLS
from app.agents.graph import get_commerce_graph


def test_initial_state():
    """Verify initial state construction."""
    state = initial_state(conversation_id="test-conv", user_id="test-user")
    assert state["conversation_id"] == "test-conv"
    assert state["user_id"] == "test-user"
    assert state["intent"] == "unknown"
    assert state["confidence"] == 0.0
    assert state["requires_escalation"] is False


def test_supervisor_rule_based_routing():
    """Verify rule-based routing fallback logic."""
    state = initial_state(conversation_id="c1", user_id="u1")

    # Order query
    res = _rule_based_routing(state, "Where is my order CF-20260718-042?")
    assert res["intent"] == "order"
    assert res["selected_agent"] == "order_agent"
    assert res["order_context"]["order_number"] == "CF-20260718-042"

    # Product query
    res2 = _rule_based_routing(state, "Recommend some wireless bluetooth headphones under 5000")
    assert res2["intent"] == "product"
    assert res2["selected_agent"] == "product_agent"

    # Regression: product browse phrasing without "product"/"recommend"
    res2b = _rule_based_routing(state, "Find wireless bluetooth earbuds")
    assert res2b["intent"] == "product"
    assert res2b["selected_agent"] == "product_agent"

    # Refund query
    res3 = _rule_based_routing(state, "I want to return a damaged item for refund")
    assert res3["intent"] == "refund"
    assert res3["selected_agent"] == "refund_agent"

    # Knowledge query
    res4 = _rule_based_routing(state, "What is your return policy and shipping time?")
    assert res4["intent"] == "knowledge"
    assert res4["selected_agent"] == "rag_agent"

    # Escalation query
    res5 = _rule_based_routing(state, "I need to talk to a human manager right now")
    assert res5["intent"] == "escalation"
    assert res5["selected_agent"] == "escalation_node"


def test_product_search_tool():
    """Verify product search tool execution."""
    output = PRODUCT_TOOLS[0].invoke({"query": "Wireless"})
    assert isinstance(output, str)
    assert "Wireless" in output or "Found" in output or "No products" in output


def test_rag_knowledge_tool():
    """Verify RAG tool execution with FAISS index."""
    output = RAG_TOOLS[0].invoke({"query": "return window policy", "top_k": 3})
    assert isinstance(output, str)
    assert "return" in output.lower() or "policy" in output.lower() or "No relevant" in output


def test_compiled_graph():
    """Verify LangGraph compiles without errors."""
    graph = get_commerce_graph()
    assert graph is not None


def test_full_graph_execution():
    """Verify end-to-end LangGraph execution on a sample query."""
    state = initial_state(conversation_id="test-conv-123", user_id="00000000-0000-0000-0000-000000000000")
    from langchain_core.messages import HumanMessage
    state["messages"] = [HumanMessage(content="What is your return policy for electronics?")]

    graph = get_commerce_graph()
    final_state = graph.invoke(state)

    assert final_state["response"] != ""
    assert final_state["intent"] in ["knowledge", "general", "refund"]
    assert final_state["selected_agent"] != ""
    assert isinstance(final_state["confidence"], float)
