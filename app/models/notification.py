import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, Index, JSON, SmallInteger,
    String, Text, func, TIMESTAMP, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    # 0=critical, 1=high, 2=normal, 3=low — lower number means higher urgency
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    template_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON works on both SQLite (tests) and PostgreSQL (prod uses JSONB via dialect)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'queued', 'sent', 'delivered', 'failed')",
            name="ck_notifications_status",
        ),
        CheckConstraint(
            "channel IN ('email', 'sms', 'push')",
            name="ck_notifications_channel",
        ),
        CheckConstraint("priority BETWEEN 0 AND 3", name="ck_notifications_priority"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )
