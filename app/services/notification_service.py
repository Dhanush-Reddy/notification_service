from __future__ import annotations

import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notification_repo import NotificationRepository
from app.repositories.preference_repo import PreferenceRepository
from app.schemas.notification import PRIORITY_MAP, NotificationCreate
from app.services import template_service
from app.services.rate_limiter import RateLimitExceeded, check_rate_limit
from app.queue.priority_queue import enqueue

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis):
        self.session = session
        self.redis = redis
        self.notif_repo = NotificationRepository(session)
        self.pref_repo = PreferenceRepository(session)

    async def send(self, payload: NotificationCreate) -> list:
        """Orchestrate a notification request across one or more channels.

        Returns a list of Notification records — one per channel.
        Raises RateLimitExceeded if user is over quota.
        """
        # rate limit is per-user across all channels combined
        await check_rate_limit(payload.user_id, self.redis)

        results = []
        for channel in payload.channels:
            notif = await self._handle_channel(payload, channel)
            if notif is not None:
                results.append(notif)

        await self.session.commit()
        return results

    async def _handle_channel(self, payload: NotificationCreate, channel: str):
        # skip if user opted out
        enabled = await self.pref_repo.is_channel_enabled(payload.user_id, channel)
        if not enabled:
            logger.info(
                "Skipping channel=%s for user=%s — opted out", channel, payload.user_id
            )
            return None

        # idempotency — if a key is provided, derive a per-channel key
        idem_key: str | None = None
        if payload.idempotency_key:
            idem_key = f"{payload.idempotency_key}:{channel}"
            existing = await self.notif_repo.get_by_idempotency_key(idem_key)
            if existing:
                logger.info("Idempotent request — returning existing notification %s", existing.id)
                return existing

        # render body from template if provided, otherwise use raw body
        body = payload.body
        subject = payload.subject
        if payload.template_id:
            body, subject = await self._resolve_template(
                payload.template_id, channel, payload.variables or {}
            )
        elif payload.variables:
            body = template_service.render(body, payload.variables)

        priority_int = PRIORITY_MAP[payload.priority]

        try:
            notif = await self.notif_repo.create(
                id=uuid.uuid4(),
                user_id=payload.user_id,
                channel=channel,
                priority=priority_int,
                template_id=payload.template_id,
                subject=subject,
                body=body,
                idempotency_key=idem_key,
                metadata_=payload.metadata,
            )
        except IntegrityError:
            # race condition on idempotency key — another request beat us to it
            await self.session.rollback()
            return await self.notif_repo.get_by_idempotency_key(idem_key)

        await enqueue(str(notif.id), priority_int, self.redis)
        await self.notif_repo.mark_queued(notif.id)

        return notif

    async def _resolve_template(
        self, template_id: str, channel: str, variables: dict[str, Any]
    ) -> tuple[str, str | None]:
        from sqlalchemy import select
        from app.models.template import NotificationTemplate

        result = await self.session.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.id == template_id,
                NotificationTemplate.channel == channel,
            )
        )
        tmpl = result.scalar_one_or_none()
        if tmpl is None:
            raise ValueError(f"Template '{template_id}' not found for channel '{channel}'")

        body = template_service.render(tmpl.body, variables)
        subject = template_service.render(tmpl.subject, variables) if tmpl.subject else None
        return body, subject
