"""Shared fixtures for all tests."""
from __future__ import annotations

import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.api.dependencies import get_db, get_redis

# SQLite in-memory — no Postgres needed to run tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_redis():
    """Fake Redis — pipeline returns counts that keep us under the rate limit."""
    redis = AsyncMock()
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, 1, 1, True])  # zremrange, zadd, zcard=1, expire
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    redis.pipeline = MagicMock(return_value=pipe)
    redis.zadd = AsyncMock(return_value=1)
    redis.zpopmin = AsyncMock(return_value=[])
    return redis


@pytest_asyncio.fixture
async def client(db_session, mock_redis):
    from app.main import create_app

    test_app = create_app()
    test_app.dependency_overrides[get_db] = lambda: db_session
    test_app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as ac:
        yield ac
