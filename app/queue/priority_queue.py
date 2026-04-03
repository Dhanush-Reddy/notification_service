import time

import redis.asyncio as aioredis

QUEUE_KEY = "notif:queue"

# Score puts lower priority numbers (critical=0) first.
# Timestamp as tiebreaker keeps things roughly FIFO within a tier.
_PRIORITY_MULTIPLIER = 1_000_000_000_000


async def enqueue(notification_id: str, priority: int, redis: aioredis.Redis) -> None:
    score = priority * _PRIORITY_MULTIPLIER + int(time.time() * 1000)
    await redis.zadd(QUEUE_KEY, {notification_id: score})


async def dequeue(count: int, redis: aioredis.Redis) -> list[str]:
    items = await redis.zpopmin(QUEUE_KEY, count)
    return [item[0] for item in items]


async def requeue_after_delay(
    notification_id: str, priority: int, delay_seconds: float, redis: aioredis.Redis
) -> None:
    future_ts = (time.time() + delay_seconds) * 1000
    score = priority * _PRIORITY_MULTIPLIER + int(future_ts)
    await redis.zadd(QUEUE_KEY, {notification_id: score})
