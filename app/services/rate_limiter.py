import time
import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

RATE_LIMIT_PREFIX = "notif:ratelimit:"


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


async def check_rate_limit(user_id: str, redis: aioredis.Redis) -> None:
    """Sliding window rate limiter — max N requests per window per user.

    Uses Redis sorted set where score = timestamp. We remove entries
    outside the window then count what's left.
    """
    key = f"{RATE_LIMIT_PREFIX}{user_id}"
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds

    pipe = redis.pipeline()
    # atomic: remove old entries, add current, count, set expiry
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, settings.rate_limit_window_seconds)
    results = await pipe.execute()

    count = results[2]  # zcard result
    if count > settings.rate_limit_max:
        # figure out when the oldest entry will age out
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        retry_after = settings.rate_limit_window_seconds
        if oldest:
            oldest_ts = oldest[0][1]
            retry_after = int(settings.rate_limit_window_seconds - (now - oldest_ts)) + 1

        # undo the zadd we just did — we're rejecting this request
        await redis.zrem(key, str(now))
        raise RateLimitExceeded(retry_after=retry_after)
