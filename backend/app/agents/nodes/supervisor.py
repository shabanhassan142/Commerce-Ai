"""
app/agents/nodes/supervisor.py

Module 10 — Supervisor (Router Node)

In Module 10, intent classification has been moved to intent_classifier_node.
The supervisor now acts purely as a ROUTER — it reads the resolved_intent
from state and maps it to the correct agent node.

The legacy LLM classification is preserved as a fallback when resolved_intent
is missing (e.g., when running tests against the old code path).
"""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage

from app.agents.state import CommerceFlowState
from app.core.logging import get_logger

logger = get_logger(__name__)

# Map resolved_intent → agent node
_INTENT_TO_AGENT = {
    # General / conversational
    "GREETING": "response_agent",
    "GENERAL_CONVERSATION": "response_agent",
    # Product detail queries (single product)
    "PRODUCT_INFORMATION": "product_agent",
    "PRODUCT_EXACT_LOOKUP": "product_agent",
    "PRICE_QUERY": "product_agent",
    "STOCK_QUERY": "product_agent",
    "RATING_QUERY": "product_agent",
    "ATTRIBUTE_QUERY": "product_agent",
    # Product search / discovery
    "PRODUCT_SEARCH": "product_agent",
    "PRODUCT_RECOMMENDATION": "product_agent",
    "PRODUCT_COMPARISON": "product_agent",
    # Order
    "ORDER_STATUS": "order_agent",
    "ORDER_HISTORY": "order_agent",
    # Policy / knowledge base
    "CART_HELP": "rag_agent",
    "SHIPPING_QUESTION": "rag_agent",
    "PAYMENT_QUESTION": "rag_agent",
    "RETURN_REFUND_QUESTION": "refund_agent",
    # Support
    "SUPPORT_REQUEST": "escalation_node",
    # Fallback
    "UNKNOWN": "response_agent",
}


def supervisor_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    Supervisor/Router node.

    Reads resolved_intent (set by intent_classifier_node) and maps to the
    correct specialist agent. Updates selected_agent in state.
    """
    resolved_intent = state.get("resolved_intent", "UNKNOWN")
    agent = _INTENT_TO_AGENT.get(resolved_intent, "response_agent")

    logger.info(f"Supervisor routing: {resolved_intent} → {agent}")

    # If resolved_intent is not set (legacy fallback), do lightweight keyword routing
    if resolved_intent == "UNKNOWN" and not state.get("intent"):
        messages = state.get("messages", [])
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )
        if last_human:
            agent = _quick_route(last_human.content)
            resolved_intent = "UNKNOWN"

    return {
        **state,
        "selected_agent": agent,
        "error": None,
    }


def _quick_route(message: str) -> str:
    """
    Ultra-lightweight keyword routing for fallback when no resolved_intent.
    Does NOT use LLM. Returns agent name.
    """
    msg = message.lower()
    order_pattern = re.compile(r"cf-\d{8}-\d+", re.IGNORECASE)

    if any(w in msg for w in ["hello", "hi ", "hey ", "thanks", "thank you"]):
        return "response_agent"
    if order_pattern.search(msg) or any(w in msg for w in ["my order", "track", "delivery"]):
        return "order_agent"
    if any(w in msg for w in ["return", "refund", "exchange", "damaged"]):
        return "refund_agent"
    if any(w in msg for w in ["shipping", "delivery time", "free shipping"]):
        return "rag_agent"
    if any(w in msg for w in ["payment", "pay method", "cod"]):
        return "rag_agent"
    if any(w in msg for w in ["human", "agent", "escalate", "manager"]):
        return "escalation_node"
    if any(w in msg for w in ["product", "price", "stock", "available", "buy", "recommend",
                               "compare", "show me", "bluetooth", "headphone", "speaker", "laptop"]):
        return "product_agent"
    return "response_agent"


def route_after_supervisor(state: CommerceFlowState) -> str:
    """Conditional edge: return the agent node name to route to."""
    return state.get("selected_agent", "response_agent")
