"""
app/models/conversation.py

Conversation and AgentLog models.
Conversations track AI chat sessions.
AgentLogs record every message/action within a conversation.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Conversation(Base):
    """AI chat session with a customer."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="New Conversation",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="conversations", lazy="selectin")
    logs = relationship(
        "AgentLog", back_populates="conversation", lazy="noload",
        order_by="AgentLog.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} title={self.title}>"


class MessageRole(str, enum.Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentLog(Base):
    """
    Log of an AI agent action/message within a conversation.
    Records which agent handled the message, the content,
    classified intent, confidence, tool calls, and performance metrics.
    """

    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="supervisor",
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="messagerole", native_enum=False),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI metadata
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Performance metrics
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    conversation = relationship("Conversation", back_populates="logs")

    def __repr__(self) -> str:
        return f"<AgentLog agent={self.agent_name} role={self.role}>"
