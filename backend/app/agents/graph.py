"""
app/agents/graph.py

CommerceFlow AI LangGraph StateGraph definition — Module 10.

Graph topology (Module 10):
  START
    ↓
  intent_classifier_node    ← classifies intent (19 fine-grained intents)
    ↓
  context_resolver_node     ← resolves active_product (pronouns, product_id, name)
    ↓
  supervisor_node           ← routes to specialist agent based on resolved_intent
    ↓ (conditional edge)
  ┌─────┬──────────┬────────────┬──────────────┐
  ↓     ↓          ↓            ↓              ↓
order  product   refund       rag_agent   escalation_node
  └─────┴──────────┴────────────┘
            ↓
       response_agent        ← synthesizes final answer
            ↓ (conditional edge)
      ┌─────────────────┐
      ↓                 ↓
   __end__      escalation_node  ← if confidence < 0.4
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.agents.nodes.context_resolver import context_resolver_node
from app.agents.nodes.escalation import escalation_node
from app.agents.nodes.intent_classifier import intent_classifier_node
from app.agents.nodes.order_agent import order_agent_node
from app.agents.nodes.product_agent import product_agent_node
from app.agents.nodes.rag_agent import rag_agent_node
from app.agents.nodes.refund_agent import refund_agent_node
from app.agents.nodes.response_agent import response_agent_node, route_after_response
from app.agents.nodes.supervisor import route_after_supervisor, supervisor_node
from app.agents.state import CommerceFlowState
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_commerce_graph():
    """Build and compile the CommerceFlow LangGraph workflow."""
    graph = StateGraph(CommerceFlowState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    # Module 10 new nodes
    graph.add_node("intent_classifier_node", intent_classifier_node)
    graph.add_node("context_resolver_node", context_resolver_node)
    # Existing nodes
    graph.add_node("supervisor_node", supervisor_node)
    graph.add_node("order_agent", order_agent_node)
    graph.add_node("product_agent", product_agent_node)
    graph.add_node("refund_agent", refund_agent_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("response_agent", response_agent_node)
    graph.add_node("escalation_node", escalation_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    # Module 10: intent_classifier is the new entry point
    graph.set_entry_point("intent_classifier_node")

    # ── Intent classifier → Context resolver ──────────────────────────────────
    graph.add_edge("intent_classifier_node", "context_resolver_node")

    # ── Context resolver → Supervisor (router) ────────────────────────────────
    graph.add_edge("context_resolver_node", "supervisor_node")

    # ── Supervisor → Specialist agents (conditional routing) ───────────────────
    graph.add_conditional_edges(
        "supervisor_node",
        route_after_supervisor,
        {
            "order_agent": "order_agent",
            "product_agent": "product_agent",
            "refund_agent": "refund_agent",
            "rag_agent": "rag_agent",
            "escalation_node": "escalation_node",
            "response_agent": "response_agent",  # for general/greeting
        },
    )

    # ── Specialist agents → Response Agent ────────────────────────────────────
    for agent in ["order_agent", "product_agent", "refund_agent", "rag_agent"]:
        graph.add_edge(agent, "response_agent")

    # ── Response Agent → End or Escalation ────────────────────────────────────
    graph.add_conditional_edges(
        "response_agent",
        route_after_response,
        {
            "__end__": END,
            "escalation_node": "escalation_node",
        },
    )

    # ── Escalation → End ──────────────────────────────────────────────────────
    graph.add_edge("escalation_node", END)

    compiled = graph.compile()
    logger.info("CommerceFlow LangGraph (Module 10) compiled successfully")
    return compiled


@lru_cache(maxsize=1)
def get_commerce_graph():
    """Return the cached compiled graph (singleton)."""
    return build_commerce_graph()
