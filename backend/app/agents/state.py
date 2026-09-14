"""
app/agents/state.py

Shared typed state for the CommerceFlow AI LangGraph workflow.
All agent nodes read from and write to this state.

Module 10 additions:
  - active_product: currently discussed product (for context-aware follow-ups)
  - product_search_results: last search results (for refinement conversations)
  - resolved_intent: fine-grained 19-intent classification
  - product_context_source: how the active_product was resolved
  - product_id_from_detail: product UUID passed from the ProductDetail page
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CommerceFlowState(TypedDict):
    """
    Shared state passed through the entire LangGraph workflow.

    Fields (original):
        conversation_id: UUID of the Conversation record in DB.
        user_id:         UUID of the authenticated User.
        messages:        Full conversation history (HumanMessage / AIMessage).
                         Uses add_messages reducer so new messages are appended.
        intent:          High-level intent bucket (kept for backward compat).
        selected_agent:  Which agent node handled the request.
        tool_results:    List of raw tool call results.
        retrieved_documents: RAG search results with text + score + metadata.
        order_context:   Loaded order data if intent is order-related.
        response:        Final answer string from response_agent.
        citations:       Source references added when RAG is used.
        confidence:      Float 0.0-1.0 — how confident the agent is.
        requires_escalation: True if human handoff is needed.
        escalation_reason:   Explanation for why escalation was triggered.
        ticket_id:       UUID of created SupportTicket (if escalated).
        error:           Any error message from tool/agent failure.

    Fields (Module 10 additions):
        active_product:         Currently-discussed product dict
                                {id, name, sku, brand, price, stock, rating,
                                 review_count, discount_percent, description,
                                 specifications}.
                                Set by context_resolver_node from:
                                  - product_id_from_detail (ProductDetail page)
                                  - explicit product name in message
                                  - pronoun resolution from conversation history
        product_search_results: List of product dicts from the last search.
                                Used to refine results ("under PKR 20,000").
        resolved_intent:        Fine-grained 19-intent classification string.
                                One of: GREETING | GENERAL_CONVERSATION |
                                PRODUCT_INFORMATION | PRODUCT_EXACT_LOOKUP |
                                PRICE_QUERY | STOCK_QUERY | RATING_QUERY |
                                ATTRIBUTE_QUERY | PRODUCT_SEARCH |
                                PRODUCT_RECOMMENDATION | PRODUCT_COMPARISON |
                                ORDER_STATUS | ORDER_HISTORY | CART_HELP |
                                SHIPPING_QUESTION | PAYMENT_QUESTION |
                                RETURN_REFUND_QUESTION | SUPPORT_REQUEST |
                                UNKNOWN
        product_context_source: How active_product was established.
                                "detail_page" | "search" | "conversation" | None
        product_id_from_detail: Raw UUID string passed from ProductDetail → Chat
                                navigation state. Cleared after resolution.
    """

    conversation_id: str
    user_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    selected_agent: str
    tool_results: list[dict[str, Any]]
    retrieved_documents: list[dict[str, Any]]
    order_context: dict[str, Any] | None
    response: str
    citations: list[dict[str, Any]]
    confidence: float
    requires_escalation: bool
    escalation_reason: str | None
    ticket_id: str | None
    error: str | None

    # ── Module 10 additions ───────────────────────────────────────────────────
    active_product: dict[str, Any] | None
    product_search_results: list[dict[str, Any]]
    resolved_intent: str
    product_context_source: str | None
    product_id_from_detail: str | None


def initial_state(
    conversation_id: str,
    user_id: str,
    messages: list[BaseMessage] | None = None,
    product_id_from_detail: str | None = None,
) -> CommerceFlowState:
    """Create a fresh state with safe defaults."""
    return CommerceFlowState(
        conversation_id=conversation_id,
        user_id=user_id,
        messages=messages or [],
        intent="unknown",
        selected_agent="",
        tool_results=[],
        retrieved_documents=[],
        order_context=None,
        response="",
        citations=[],
        confidence=0.0,
        requires_escalation=False,
        escalation_reason=None,
        ticket_id=None,
        error=None,
        # Module 10
        active_product=None,
        product_search_results=[],
        resolved_intent="UNKNOWN",
        product_context_source=None,
        product_id_from_detail=product_id_from_detail,
    )
