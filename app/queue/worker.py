from __future__ import annotations

import asyncio
import logging
import uuid

import redis.asyncio as aioredis

from app.config import settings
from app.database import AsyncSessionLocal
from app.providers import get_provider
from app.queue.priority_queue import dequeue, requeue_after_delay
from app.repositories.notification_repo import NotificationRepository
from app.services.retry import MAX_RETRIES, compute_next_retry, should_retry

logger = logging.getLogger(__name__)


async def run_worker(redis: aioredis.Redis) -> None:
    """Main worker loop — drains the priority queue and dispatches notifications."""
    logger.info("Worker started, polling every %.1fs", settings.worker_poll_interval)
    while True:
        try:
            ids = await dequeue(settings.worker_batch_size, redis)
            if not ids:
                await asyncio.sleep(settings.worker_poll_interval)
                continue

            tasks = [_process(nid, redis) for nid in ids]
            await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            logger.info("Worker shutting down")
            raise
        except Exception:
            # don't let an unexpected error kill the worker loop
            logger.exception("Unexpected error in worker loop")
            await asyncio.sleep(1)


async def _process(notification_id: str, redis: aioredis.Redis) -> None:
    async with AsyncSessionLocal() as session:
        repo = NotificationRepository(session)
        notif = await repo.get(uuid.UUID(notification_id))

        if notif is None:
            logger.warning("Notification %s not found, skipping", notification_id)
            return

        if notif.status == "failed":
            # was marked failed elsewhere (e.g. manual override) — skip
            return

        provider = get_provider(notif.channel)
        try:
            await provider.send(notif)
            await repo.mark_sent(notif.id)
            await session.commit()
            logger.info("Sent notification %s via %s", notif.id, notif.channel)

        except Exception as exc:
            logger.warning(
                "Provider failed for notification %s: %s", notification_id, exc
            )
            await _handle_failure(notif, exc, repo, redis, session)


async def _handle_failure(notif, error, repo, redis, session) -> None:
    if not should_retry(notif.retry_count):
        await repo.mark_failed(notif.id, str(error))
        await session.commit()
        logger.error(
            "Notification %s permanently failed after %d retries",
            notif.id,
            notif.retry_count,
        )
        return

    delay = compute_next_retry(notif.retry_count)
    await repo.schedule_retry(notif.id, delay)
    await session.commit()

    await requeue_after_delay(str(notif.id), notif.priority, delay, redis)
    logger.info(
        "Scheduled retry %d/%d for notification %s in %.1fs",
        notif.retry_count,
        MAX_RETRIES,
        notif.id,
        delay,
    )
