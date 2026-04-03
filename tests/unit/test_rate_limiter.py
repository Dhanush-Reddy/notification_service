"""Unit tests for the sliding window rate limiter."""
from __future__ import annotations

import time
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.rate_limiter import check_rate_limit, RateLimitExceeded
from app.config import settings


def _make_redis_pipe(zcard_result: int):
    """Build a mock Redis pipeline that returns zcard_result as the count."""
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, 1, zcard_result, True])
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    return pipe


@pytest.mark.asyncio
async def test_under_limit_passes():
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=_make_redis_pipe(1))
    # should not raise
    await check_rate_limit("user_1", redis)


@pytest.mark.asyncio
async def test_at_limit_passes():
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=_make_redis_pipe(settings.rate_limit_max))
    await check_rate_limit("user_1", redis)


@pytest.mark.asyncio
async def test_over_limit_raises():
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=_make_redis_pipe(settings.rate_limit_max + 1))
    now = time.time()
    redis.zrange = AsyncMock(return_value=[("entry", now - 10)])
    redis.zrem = AsyncMock()

    with pytest.raises(RateLimitExceeded) as exc_info:
        await check_rate_limit("user_1", redis)

    assert exc_info.value.retry_after > 0


@pytest.mark.asyncio
async def test_rate_limit_exceeded_has_retry_after():
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=_make_redis_pipe(settings.rate_limit_max + 5))
    now = time.time()
    redis.zrange = AsyncMock(return_value=[("entry", now - 100)])
    redis.zrem = AsyncMock()

    with pytest.raises(RateLimitExceeded) as exc_info:
        await check_rate_limit("user_xyz", redis)

    # retry_after should be roughly window - elapsed time
    assert exc_info.value.retry_after == pytest.approx(
        settings.rate_limit_window_seconds - 100, abs=2
    )
