import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, String, UniqueConstraint, func, TIMESTAMP, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base



class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_user_preferences_user_channel"),
        CheckConstraint(
            "channel IN ('email', 'sms', 'push')",
            name="ck_user_preferences_channel",
        ),
    )
