"""
app/agents/memory.py

Conversation memory persistence.
Saves and loads conversation history from the PostgreSQL Conversation + AgentLog models.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

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


async def _load_history_async(conversation_id: str) -> list[dict]:
    """Load message history from the DB."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.models.conversation import AgentLog

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(
                select(AgentLog)
                .where(AgentLog.conversation_id == uuid.UUID(conversation_id))
                .order_by(AgentLog.created_at.asc())
                .limit(20)  # last 20 log entries = ~10 turns
            )
            logs = result.scalars().all()
            return [
                {
                    "role": log.role.value if hasattr(log.role, "value") else str(log.role),
                    "content": log.content,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
    finally:
        await engine.dispose()


async def _save_turn_async(
    conversation_id: str,
    user_id: str,
    human_message: str,
    ai_message: str,
    intent: str,
    agent: str,
    confidence: float,
    tool_results: list[dict],
    ticket_id: str | None,
) -> None:
    """Persist a conversation turn to the DB."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.models.conversation import AgentLog, Conversation, MessageRole
    from sqlalchemy import update

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as session:
            conv_id = uuid.UUID(conversation_id)

            # Update conversation timestamp
            await session.execute(
                update(Conversation)
                .where(Conversation.id == conv_id)
                .values(last_message_at=datetime.now(timezone.utc))
            )

            # Save human message
            human_log = AgentLog(
                id=uuid.uuid4(),
                conversation_id=conv_id,
                role=MessageRole.USER,
                content=human_message,
                agent_name="user",
                intent=intent,
            )
            session.add(human_log)

            # Save AI message
            ai_log = AgentLog(
                id=uuid.uuid4(),
                conversation_id=conv_id,
                role=MessageRole.ASSISTANT,
                content=ai_message,
                agent_name=agent,
                intent=intent,
                confidence=confidence,
                tool_calls={"results": tool_results[:3], "ticket_id": ticket_id} if (tool_results or ticket_id) else None,
            )
            session.add(ai_log)

            await session.commit()
            logger.debug(f"Saved turn to conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Failed to save conversation turn: {e}", exc_info=True)
    finally:
        await engine.dispose()


async def _create_conversation_async(user_id: str) -> str:
    """Create a new Conversation record for a customer and return its ID."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.models.conversation import Conversation
    from app.models.customer import Customer

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Get customer_id
            cust_result = await session.execute(
                select(Customer).where(Customer.user_id == user_id)
            )
            customer = cust_result.scalar_one_or_none()
            if not customer:
                customer = Customer(user_id=user_id)
                session.add(customer)
                await session.commit()
                await session.refresh(customer)

            conv = Conversation(
                id=uuid.uuid4(),
                customer_id=customer.id,
                title="AI Support Chat",
                is_active=True,
                last_message_at=datetime.now(timezone.utc),
            )
            session.add(conv)
            await session.commit()
            return str(conv.id)
    finally:
        await engine.dispose()


# ── Public API ─────────────────────────────────────────────────────────────────

def load_conversation_history(conversation_id: str) -> list[BaseMessage]:
    """
    Load past messages for a conversation from the DB.
    Returns a list of LangChain BaseMessage objects.
    """
    try:
        raw_logs = _run(_load_history_async(conversation_id))
        messages: list[BaseMessage] = []
        for log in raw_logs:
            if log["role"] == "user":
                messages.append(HumanMessage(content=log["content"]))
            elif log["role"] == "assistant":
                messages.append(AIMessage(content=log["content"]))
        return messages
    except Exception as e:
        logger.error(f"Failed to load conversation history: {e}", exc_info=True)
        return []


def save_conversation_turn(
    conversation_id: str,
    user_id: str,
    human_message: str,
    ai_message: str,
    intent: str = "unknown",
    agent: str = "unknown",
    confidence: float = 0.5,
    tool_results: list[dict] | None = None,
    ticket_id: str | None = None,
) -> None:
    """Save a completed conversation turn to the database."""
    try:
        _run(_save_turn_async(
            conversation_id=conversation_id,
            user_id=user_id,
            human_message=human_message,
            ai_message=ai_message,
            intent=intent,
            agent=agent,
            confidence=confidence,
            tool_results=tool_results or [],
            ticket_id=ticket_id,
        ))
    except Exception as e:
        logger.error(f"Failed to save conversation turn: {e}", exc_info=True)


def create_conversation(user_id: str) -> str:
    """Create a new conversation record and return the conversation_id."""
    try:
        return _run(_create_conversation_async(user_id))
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}", exc_info=True)
        return str(uuid.uuid4())
