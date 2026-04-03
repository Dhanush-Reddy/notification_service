from datetime import datetime

from sqlalchemy import CheckConstraint, String, Text, func, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    # using string ID so callers can reference templates by name, e.g. "order_shipped"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)  # email only
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms', 'push')",
            name="ck_templates_channel",
        ),
    )
