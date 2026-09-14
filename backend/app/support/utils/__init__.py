"""Support utility helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.ticket import SLA_HOURS, TicketPriority, TicketStatus, VALID_STATUS_TRANSITIONS


def compute_sla_deadline(
    priority: TicketPriority,
    from_time: datetime | None = None,
) -> datetime:
    """Compute SLA deadline from priority hours."""
    base = from_time or datetime.now(timezone.utc)
    hours = SLA_HOURS.get(priority, 24)
    return base + timedelta(hours=hours)


def normalize_status(status: TicketStatus | str) -> TicketStatus:
    """Normalize legacy WAITING → WAITING_FOR_CUSTOMER."""
    if isinstance(status, str):
        status = TicketStatus(status)
    if status == TicketStatus.WAITING:
        return TicketStatus.WAITING_FOR_CUSTOMER
    return status


def can_transition(current: TicketStatus | str, new: TicketStatus | str) -> bool:
    """Validate status transition against lifecycle rules."""
    cur = normalize_status(current)
    nxt = normalize_status(new) if new != TicketStatus.WAITING else TicketStatus.WAITING_FOR_CUSTOMER
    if isinstance(new, str):
        try:
            nxt = TicketStatus(new)
            if nxt == TicketStatus.WAITING:
                nxt = TicketStatus.WAITING_FOR_CUSTOMER
        except ValueError:
            return False
    allowed = VALID_STATUS_TRANSITIONS.get(cur, set())
    # Also allow transitioning from WAITING legacy
    if cur == TicketStatus.WAITING:
        allowed = VALID_STATUS_TRANSITIONS[TicketStatus.WAITING]
    return nxt in allowed or nxt == cur


def suggest_department(intent: str | None) -> str:
    """Map classified intent to a suggested support department."""
    mapping = {
        "order": "Order Support",
        "product": "Product Support",
        "refund": "Returns & Refunds",
        "knowledge": "General Support",
        "escalation": "Priority Escalations",
        "general": "General Support",
        "billing": "Billing",
    }
    return mapping.get((intent or "general").lower(), "General Support")


def suggest_priority_from_context(
    intent: str | None,
    confidence: float | None,
    explicit_priority: str | None = None,
) -> TicketPriority:
    """Suggest ticket priority from escalation context."""
    if explicit_priority:
        try:
            return TicketPriority(explicit_priority.lower())
        except ValueError:
            pass
    if intent == "escalation":
        return TicketPriority.HIGH
    if confidence is not None and confidence < 0.3:
        return TicketPriority.HIGH
    if intent == "refund":
        return TicketPriority.MEDIUM
    return TicketPriority.MEDIUM


def build_ai_summary(
    *,
    customer_message: str,
    intent: str | None,
    confidence: float | None,
    order_context: dict[str, Any] | None,
    tool_results: list[dict[str, Any]] | None,
    retrieved_documents: list[dict[str, Any]] | None,
    escalation_reason: str | None,
    selected_agent: str | None,
) -> dict[str, Any]:
    """
    Build structured AI summary so human agents skip reading the full chat.
    """
    orders_mentioned: list[str] = []
    products_mentioned: list[str] = []

    if order_context and order_context.get("order_number"):
        orders_mentioned.append(order_context["order_number"])

    for tr in tool_results or []:
        out = str(tr.get("output", ""))
        tool = tr.get("tool", "")
        if "order" in tool.lower() and "CF-" in out:
            for token in out.split():
                if token.upper().startswith("CF-"):
                    cleaned = token.strip(".,")
                    if cleaned not in orders_mentioned:
                        orders_mentioned.append(cleaned)
        if "product" in tool.lower() or "SKU-" in out:
            for line in out.splitlines():
                if "SKU:" in line:
                    products_mentioned.append(line.strip())

    knowledge_snippets = []
    for doc in (retrieved_documents or [])[:5]:
        knowledge_snippets.append({
            "source": (doc.get("metadata") or {}).get("source", "knowledge base"),
            "score": doc.get("score"),
            "preview": (doc.get("text") or "")[:200],
        })

    suggested_resolution = (
        "Review AI context and respond with policy-backed guidance. "
        "Confirm order/product details before promising refunds or replacements."
    )
    if intent == "refund":
        suggested_resolution = (
            "Verify return eligibility window, inspect order items, and guide "
            "the customer through the return process or approve refund if eligible."
        )
    elif intent == "order":
        suggested_resolution = (
            "Check latest shipment/tracking status and provide a clear ETA update "
            "or compensation options if delayed."
        )

    return {
        "issue_summary": customer_message[:500],
        "customer_intent": intent or "unknown",
        "relevant_orders": orders_mentioned,
        "products_mentioned": products_mentioned[:10],
        "suggested_resolution": suggested_resolution,
        "retrieved_knowledge": knowledge_snippets,
        "confidence_score": confidence,
        "selected_agent": selected_agent,
        "escalation_reason": escalation_reason,
    }


def enum_val(value: Any) -> str:
    """Extract string value from enum or passthrough."""
    return value.value if hasattr(value, "value") else str(value)
