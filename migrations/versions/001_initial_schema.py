"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("template_id", sa.String(255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("sent_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("delivered_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("failed_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'sent', 'delivered', 'failed')",
            name="ck_notifications_status",
        ),
        sa.CheckConstraint(
            "channel IN ('email', 'sms', 'push')",
            name="ck_notifications_channel",
        ),
        sa.CheckConstraint("priority BETWEEN 0 AND 3", name="ck_notifications_priority"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index(
        "ix_notifications_user_created", "notifications", ["user_id", "created_at"]
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "channel", name="uq_user_preferences_user_channel"),
        sa.CheckConstraint(
            "channel IN ('email', 'sms', 'push')",
            name="ck_user_preferences_channel",
        ),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    op.create_table(
        "notification_templates",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "channel IN ('email', 'sms', 'push')",
            name="ck_templates_channel",
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_templates")
    op.drop_table("user_preferences")
    op.drop_table("notifications")
