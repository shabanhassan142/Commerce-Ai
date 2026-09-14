"""
app/agents/nodes/escalation.py

Escalation node — creates a support ticket when confidence is low
or the customer explicitly requests human help.

Module 5: populates AI summary, conversation link, RAG docs, intent, priority.
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.state import CommerceFlowState
from app.agents.tools.ticket_tools import TICKET_TOOLS
from app.core.logging import get_logger

logger = get_logger(__name__)


def escalation_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    Escalation node: auto-create a support ticket and update the response.
    This node is reached when:
      - confidence < 0.4 after response_agent
      - intent = 'escalation' (customer explicitly asked for human)
    """
    logger.info(f"Escalation triggered for conversation {state['conversation_id']}")

    user_id = state["user_id"]
    messages = state.get("messages", [])
    intent = state.get("intent", "unknown")

    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    customer_message = last_human.content if last_human else "No message provided"

    tool_results = state.get("tool_results", [])
    has_errors = any("error" in str(r.get("output", "")).lower() for r in tool_results)
    confidence = float(state.get("confidence") or 0)

    if intent == "escalation":
        subject = "Customer requested human support"
        priority = "high"
        reason = "Customer explicitly requested human agent assistance"
    elif has_errors:
        subject = f"Automated agent could not resolve: {customer_message[:60]}"
        priority = "medium"
        reason = f"Tools returned errors. Low confidence ({confidence:.2f})"
    else:
        subject = f"Low-confidence response: {customer_message[:60]}"
        priority = "high" if confidence < 0.3 else "medium"
        reason = f"Confidence too low ({confidence:.2f}) to trust automated response"

    description = (
        f"Customer Message: {customer_message}\n"
        f"Intent Detected: {intent}\n"
        f"Agent Used: {state.get('selected_agent', 'unknown')}\n"
        f"Confidence: {confidence:.2f}\n"
        f"Reason for Escalation: {reason}"
    )

    order_number = ""
    order_context = state.get("order_context") or {}
    if order_context:
        order_number = order_context.get("order_number", "") or ""

    retrieved_docs = state.get("retrieved_documents") or []

    ticket_result = TICKET_TOOLS[0].invoke({
        "user_id": user_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "order_number": order_number,
        "conversation_id": state.get("conversation_id") or "",
        "intent": intent or "",
        "confidence": confidence,
        "escalation_reason": reason,
        "selected_agent": state.get("selected_agent") or "",
        "order_context_json": json.dumps(order_context) if order_context else "",
        "tool_results_json": json.dumps(tool_results, default=str) if tool_results else "",
        "retrieved_documents_json": json.dumps(retrieved_docs, default=str) if retrieved_docs else "",
        "customer_message": customer_message,
    })

    ticket_number = None
    for line in ticket_result.split("\n"):
        if "Ticket Number:" in line:
            ticket_number = line.split("Ticket Number:")[-1].strip()
            break

    if intent == "escalation":
        escalation_message = (
            "Of course! I've connected you with our human support team.\n\n"
            f"{ticket_result}\n\n"
            "A support agent will review your case and get back to you within 24 hours. "
            "You can track your ticket status in My Account > Support Tickets."
        )
    else:
        current_response = state.get("response", "")
        escalation_message = (
            f"{current_response}\n\n"
            "---\n"
            "I've also created a support ticket so our team can follow up:\n\n"
            f"{ticket_result}\n\n"
            "A human agent will review your case within 24 hours."
        )

    messages_copy = list(state.get("messages", []))
    if messages_copy and isinstance(messages_copy[-1], AIMessage):
        messages_copy[-1] = AIMessage(content=escalation_message)
    else:
        messages_copy.append(AIMessage(content=escalation_message))

    return {
        **state,
        "response": escalation_message,
        "requires_escalation": False,
        "escalation_reason": reason,
        "ticket_id": ticket_number,
        "messages": messages_copy,
    }
