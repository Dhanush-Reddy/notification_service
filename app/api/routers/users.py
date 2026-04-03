from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.repositories.notification_repo import NotificationRepository
from app.repositories.preference_repo import PreferenceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationDetail
from app.schemas.preference import PreferenceResponse, PreferenceUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{userId}/notifications", response_model=PaginatedResponse[NotificationDetail])
async def list_user_notifications(
    userId: str,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Paginated notification history for a user."""
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination params")

    repo = NotificationRepository(db)
    items, total = await repo.list_for_user(userId, page=page, limit=limit)
    return PaginatedResponse(
        items=[NotificationDetail.model_validate(n) for n in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{userId}/preferences", response_model=list[PreferenceResponse])
async def get_preferences(
    userId: str,
    db: AsyncSession = Depends(get_db),
):
    repo = PreferenceRepository(db)
    prefs = await repo.get_all(userId)
    return [PreferenceResponse.model_validate(p) for p in prefs]


@router.post("/{userId}/preferences", response_model=PreferenceResponse)
async def set_preference(
    userId: str,
    payload: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Upsert a channel preference for a user.

    Creates the preference row if it doesn't exist, updates it if it does.
    """
    repo = PreferenceRepository(db)
    pref = await repo.upsert(userId, payload.channel, payload.is_enabled)
    await db.commit()
    return PreferenceResponse.model_validate(pref)
