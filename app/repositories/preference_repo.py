import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference


class PreferenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, user_id: str) -> list[UserPreference]:
        result = await self.session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalars().all()

    async def is_channel_enabled(self, user_id: str, channel: str) -> bool:
        """Return True if user has not explicitly disabled this channel.
        Defaults to enabled if no preference row exists.
        """
        result = await self.session.execute(
            select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.channel == channel,
            )
        )
        pref = result.scalar_one_or_none()
        return pref.is_enabled if pref else True

    async def upsert(self, user_id: str, channel: str, is_enabled: bool) -> UserPreference:
        """Insert or update a channel preference.

        Using select-then-update instead of dialect-specific ON CONFLICT
        so this works on both SQLite (tests) and PostgreSQL (prod).
        """
        result = await self.session.execute(
            select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.channel == channel,
            )
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = UserPreference(
                id=uuid.uuid4(),
                user_id=user_id,
                channel=channel,
                is_enabled=is_enabled,
            )
            self.session.add(pref)
        else:
            pref.is_enabled = is_enabled
            pref.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        return pref
