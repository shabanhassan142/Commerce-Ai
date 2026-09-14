"""Module 5 — Support operations: ticket lifecycle, notes, replies, timeline, audit, notifications."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "3bc2ccd4722a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extend support_tickets ────────────────────────────────────────────────
    op.add_column("support_tickets", sa.Column("conversation_id", sa.Uuid(), nullable=True))
    op.add_column("support_tickets", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("last_updated_by", sa.Uuid(), nullable=True))
    op.add_column("support_tickets", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("resolution_time_seconds", sa.Integer(), nullable=True))
    op.add_column("support_tickets", sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("intent", sa.String(length=100), nullable=True))
    op.add_column("support_tickets", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("support_tickets", sa.Column("suggested_department", sa.String(length=100), nullable=True))
    op.add_column("support_tickets", sa.Column("suggested_priority", sa.String(length=20), nullable=True))
    op.add_column("support_tickets", sa.Column("escalation_reason", sa.Text(), nullable=True))
    op.add_column(
        "support_tickets",
        sa.Column("ai_summary", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column(
            "retrieved_documents",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )
    op.add_column("support_tickets", sa.Column("customer_satisfaction", sa.Integer(), nullable=True))

    op.create_index("ix_support_tickets_conversation_id", "support_tickets", ["conversation_id"])
    op.create_index("ix_support_tickets_assigned_to", "support_tickets", ["assigned_to"])
    op.create_index("ix_support_tickets_sla_deadline", "support_tickets", ["sla_deadline"])

    op.create_foreign_key(
        "fk_support_tickets_conversation_id",
        "support_tickets",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_support_tickets_last_updated_by",
        "support_tickets",
        "users",
        ["last_updated_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Expand status column length for longer enum values (e.g., waiting_for_customer)
    op.alter_column(
        "support_tickets",
        "status",
        existing_type=sa.String(length=11),
        type_=sa.String(length=50),
        existing_nullable=False,
    )

    # Normalize legacy waiting → waiting_for_customer where present
    op.execute(
        "UPDATE support_tickets SET status = 'waiting_for_customer' WHERE status = 'waiting'"
    )

    # ── ticket_notes ──────────────────────────────────────────────────────────
    op.create_table(
        "ticket_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "edit_history",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_notes_id", "ticket_notes", ["id"])
    op.create_index("ix_ticket_notes_ticket_id", "ticket_notes", ["ticket_id"])
    op.create_index("ix_ticket_notes_author_id", "ticket_notes", ["author_id"])

    # ── ticket_replies ────────────────────────────────────────────────────────
    op.create_table(
        "ticket_replies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column(
            "author_type",
            sa.Enum("customer", "support", "system", name="replyauthortype", native_enum=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_placeholder", sa.String(length=500), nullable=True),
        sa.Column("is_ai_summary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_replies_id", "ticket_replies", ["id"])
    op.create_index("ix_ticket_replies_ticket_id", "ticket_replies", ["ticket_id"])
    op.create_index("ix_ticket_replies_author_id", "ticket_replies", ["author_id"])

    # ── ticket_timeline_events ────────────────────────────────────────────────
    op.create_table(
        "ticket_timeline_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "ticket_created",
                "ai_escalated",
                "assigned",
                "unassigned",
                "reassigned",
                "status_changed",
                "priority_changed",
                "customer_replied",
                "agent_replied",
                "note_added",
                "note_updated",
                "resolved",
                "closed",
                "reopened",
                "sla_updated",
                name="timelineeventtype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_label", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "event_data",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_timeline_events_id", "ticket_timeline_events", ["id"])
    op.create_index("ix_ticket_timeline_events_ticket_id", "ticket_timeline_events", ["ticket_id"])
    op.create_index("ix_ticket_timeline_events_event_type", "ticket_timeline_events", ["event_type"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column(
            "old_values",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "new_values",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "ticket_assigned",
                "customer_reply",
                "ticket_closed",
                "escalation_created",
                "ticket_reopened",
                "priority_changed",
                "status_changed",
                name="notificationeventtype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.Enum(
                "in_app", "email", "sms", "push", "websocket",
                name="notificationchannel",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])
    op.create_index("ix_notifications_event_type", "notifications", ["event_type"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("audit_logs")
    op.drop_table("ticket_timeline_events")
    op.drop_table("ticket_replies")
    op.drop_table("ticket_notes")

    op.drop_constraint("fk_support_tickets_last_updated_by", "support_tickets", type_="foreignkey")
    op.drop_constraint("fk_support_tickets_conversation_id", "support_tickets", type_="foreignkey")
    op.drop_index("ix_support_tickets_sla_deadline", table_name="support_tickets")
    op.drop_index("ix_support_tickets_assigned_to", table_name="support_tickets")
    op.drop_index("ix_support_tickets_conversation_id", table_name="support_tickets")

    for col in [
        "customer_satisfaction",
        "retrieved_documents",
        "ai_summary",
        "escalation_reason",
        "suggested_priority",
        "suggested_department",
        "confidence",
        "intent",
        "sla_deadline",
        "resolution_time_seconds",
        "first_response_at",
        "closed_at",
        "last_updated_by",
        "assigned_at",
        "conversation_id",
    ]:
        op.drop_column("support_tickets", col)
