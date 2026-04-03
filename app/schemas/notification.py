from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


VALID_CHANNELS = {"email", "sms", "push"}
PRIORITY_MAP = {"critical": 0, "high": 1, "normal": 2, "low": 3}


class NotificationCreate(BaseModel):
    user_id: str
    channels: list[str] = Field(..., min_length=1)
    priority: str = "normal"
    template_id: str | None = None
    subject: str | None = None
    body: str
    variables: dict[str, Any] | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_CHANNELS
        if invalid:
            raise ValueError(f"Invalid channel(s): {invalid}. Must be one of {VALID_CHANNELS}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITY_MAP:
            raise ValueError(f"priority must be one of {list(PRIORITY_MAP.keys())}")
        return v


class NotificationQueued(BaseModel):
    """Returned on 202 — notification accepted for processing."""
    id: uuid.UUID
    channel: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreateResponse(BaseModel):
    notifications: list[NotificationQueued]


class NotificationDetail(BaseModel):
    id: uuid.UUID
    user_id: str
    channel: str
    priority: int
    status: str
    subject: str | None
    body: str
    template_id: str | None
    retry_count: int
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
