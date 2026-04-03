from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Notification:
        notif = Notification(**kwargs)
        self.session.add(notif)
        await self.session.flush()
        await self.session.refresh(notif)
        return notif

    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(Notification.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, page: int = 1, limit: int = 20
    ) -> tuple[list[Notification], int]:
        offset = (page - 1) * limit
        q = select(Notification).where(Notification.user_id == user_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(q.subquery())
        )
        total = count_result.scalar_one()

        items_result = await self.session.execute(
            q.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        )
        return items_result.scalars().all(), total

    async def mark_queued(self, notification_id: uuid.UUID) -> None:
        notif = await self.get(notification_id)
        if notif:
            notif.status = "queued"
            notif.updated_at = datetime.now(timezone.utc)

    async def mark_sent(self, notification_id: uuid.UUID) -> None:
        notif = await self.get(notification_id)
        if notif:
            notif.status = "sent"
            notif.sent_at = datetime.now(timezone.utc)
            notif.updated_at = datetime.now(timezone.utc)

    async def mark_failed(self, notification_id: uuid.UUID, error: str) -> None:
        notif = await self.get(notification_id)
        if notif:
            notif.status = "failed"
            notif.failed_at = datetime.now(timezone.utc)
            notif.error_message = error
            notif.updated_at = datetime.now(timezone.utc)

    async def schedule_retry(
        self, notification_id: uuid.UUID, delay_seconds: float
    ) -> None:
        from datetime import timedelta
        notif = await self.get(notification_id)
        if notif:
            notif.retry_count += 1
            notif.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            notif.status = "pending"
            notif.updated_at = datetime.now(timezone.utc)
