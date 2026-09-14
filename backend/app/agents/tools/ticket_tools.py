"""
app/agents/tools/ticket_tools.py

Tools for support ticket creation and lookup.
Module 5: enriched AI escalation with summary, SLA, timeline, notifications.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.tools import tool

from app.core.logging import get_logger

logger = get_logger(__name__)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _create_ticket_async(
    user_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    order_number: str | None = None,
    conversation_id: str | None = None,
    intent: str | None = None,
    confidence: float | None = None,
    escalation_reason: str | None = None,
    selected_agent: str | None = None,
    order_context_json: str = "",
    tool_results_json: str = "",
    retrieved_documents_json: str = "",
    customer_message: str = "",
) -> dict[str, Any]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.support.services import TicketService

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    def _loads(raw: str):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    try:
        async with async_session() as session:
            service = TicketService(session)
            return await service.create_from_escalation(
                user_id=user_id,
                subject=subject,
                description=description,
                priority=priority,
                order_number=order_number,
                conversation_id=conversation_id,
                intent=intent,
                confidence=confidence,
                escalation_reason=escalation_reason,
                selected_agent=selected_agent,
                order_context=_loads(order_context_json),
                tool_results=_loads(tool_results_json),
                retrieved_documents=_loads(retrieved_documents_json),
                customer_message=customer_message,
            )
    finally:
        await engine.dispose()


@tool
def create_support_ticket(
    user_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    order_number: str = "",
    conversation_id: str = "",
    intent: str = "",
    confidence: float = 0.0,
    escalation_reason: str = "",
    selected_agent: str = "",
    order_context_json: str = "",
    tool_results_json: str = "",
    retrieved_documents_json: str = "",
    customer_message: str = "",
) -> str:
    """
    Create a support ticket for human agent review.
    Use this when: the agent cannot resolve the issue, the customer explicitly asks
    to speak to a human, the issue is complex/sensitive, or confidence is low.

    Args:
        user_id: The authenticated user's UUID string
        subject: Brief subject line for the ticket
        description: Detailed description of the customer's issue
        priority: Ticket priority - 'low', 'medium', 'high', or 'urgent'
        order_number: Optional related order number
        conversation_id: Optional conversation UUID
        intent: Classified intent from supervisor
        confidence: Agent confidence score
        escalation_reason: Why escalation was triggered
        selected_agent: Which specialist was selected
        order_context_json: JSON string of order context
        tool_results_json: JSON string of tool results
        retrieved_documents_json: JSON string of RAG docs
        customer_message: Latest customer utterance

    Returns:
        Ticket number and confirmation details
    """
    result = _run(
        _create_ticket_async(
            user_id=user_id,
            subject=subject,
            description=description,
            priority=priority,
            order_number=order_number or None,
            conversation_id=conversation_id or None,
            intent=intent or None,
            confidence=confidence if confidence else None,
            escalation_reason=escalation_reason or None,
            selected_agent=selected_agent or None,
            order_context_json=order_context_json,
            tool_results_json=tool_results_json,
            retrieved_documents_json=retrieved_documents_json,
            customer_message=customer_message,
        )
    )

    if "error" in result:
        return f"Error creating ticket: {result['error']}"

    dept = result.get("suggested_department", "General Support")
    lines = [
        "Support ticket created successfully!",
        f"  Ticket Number: {result['ticket_number']}",
        f"  Subject: {result['subject']}",
        f"  Priority: {result['priority'].upper()}",
        f"  Status: OPEN",
        f"  Suggested Department: {dept}",
        "",
        "Our support team will review your ticket and respond within 24 hours.",
        "You can track your ticket status in My Account > Support Tickets.",
    ]
    return "\n".join(lines)


TICKET_TOOLS = [create_support_ticket]
