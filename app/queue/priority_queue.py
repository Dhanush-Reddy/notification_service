import time

import redis.asyncio as aioredis

QUEUE_KEY = "notif:queue"


async def enqueue(notification_id: str, priority: int, redis: aioredis.Redis) -> None:
    """Add a notification to the priority queue.

    Score = (priority * 1e12) + timestamp_ms so that:
    - lower priority number (0=critical) sorts first (lower score)
    - within same priority, FIFO ordering by timestamp
    """
    score = priority * 1_000_000_000_000 + int(time.time() * 1000)
    await redis.zadd(QUEUE_KEY, {notification_id: score})


async def dequeue(count: int, redis: aioredis.Redis) -> list[str]:
    """Atomically pop `count` lowest-score items from the queue."""
    items = await redis.zpopmin(QUEUE_KEY, count)
    # items is a list of (member, score) tuples
    return [item[0] for item in items]


async def requeue_after_delay(
    notification_id: str, priority: int, delay_seconds: float, redis: aioredis.Redis
) -> None:
    """Schedule a notification to be re-processed after a delay.

    Score is set to a future timestamp so the worker only picks it up
    after the delay has elapsed.
    """
    future_ts = (time.time() + delay_seconds) * 1000
    score = priority * 1_000_000_000_000 + int(future_ts)
    await redis.zadd(QUEUE_KEY, {notification_id: score})
