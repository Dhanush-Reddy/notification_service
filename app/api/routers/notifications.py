from __future__ import annotations

import uuid
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_redis
from app.repositories.notification_repo import NotificationRepository
from app.schemas.notification import (
    NotificationCreate,
    NotificationCreateResponse,
    NotificationDetail,
    NotificationQueued,
)
from app.services.notification_service import NotificationService
from app.services.rate_limiter import RateLimitExceeded

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", status_code=202, response_model=NotificationCreateResponse)
async def send_notification(
    payload: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Accept a notification request and queue it for async delivery.

    Returns 202 Accepted — the notification is queued, not yet sent.
    A single request may produce multiple notification records (one per channel).
    """
    svc = NotificationService(db, redis)
    try:
        notifications = await svc.send(payload)
    except RateLimitExceeded as exc:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded. Retry after {exc.retry_after}s."},
            headers={"Retry-After": str(exc.retry_after)},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not notifications:
        raise HTTPException(
            status_code=422,
            detail="No notifications were queued — user has opted out of all requested channels.",
        )

    return NotificationCreateResponse(
        notifications=[NotificationQueued.model_validate(n) for n in notifications]
    )


@router.get("/{notification_id}", response_model=NotificationDetail)
async def get_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    notif = await repo.get(notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationDetail.model_validate(notif)
