"""
demo.py — Run the notification service with NO external dependencies.

Uses:
  - SQLite (in-memory) instead of PostgreSQL
  - FakeRedis (in-process) instead of real Redis

Start with:
    python demo.py

Then open: http://localhost:8000/docs
"""
import asyncio
import uuid
import time
import logging
from contextlib import asynccontextmanager
from collections import defaultdict
import heapq

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Patch DB to use SQLite before any app code imports database.py
# ---------------------------------------------------------------------------
import app.database as _db_module
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

_sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_db_module.engine = _sqlite_engine
_db_module.AsyncSessionLocal = async_sessionmaker(
    bind=_sqlite_engine, class_=AsyncSession, expire_on_commit=False
)


# ---------------------------------------------------------------------------
# Fake Redis — implements just enough for rate limiter + priority queue
# ---------------------------------------------------------------------------
class FakeRedis:
    """In-process Redis substitute. Enough for demo purposes."""

    def __init__(self):
        self._zsets: dict[str, list] = defaultdict(list)   # sorted set store
        self._data: dict[str, str] = {}

    def pipeline(self):
        return FakePipeline(self)

    async def zadd(self, key, mapping: dict):
        zset = self._zsets[key]
        members = {m for _, m in zset}
        for member, score in mapping.items():
            if member in members:
                self._zsets[key] = [(s, m) for s, m in zset if m != member]
            heapq.heappush(self._zsets[key], (score, member))

    async def zpopmin(self, key, count=1):
        results = []
        for _ in range(count):
            if not self._zsets[key]:
                break
            score, member = heapq.heappop(self._zsets[key])
            results.append((member, score))
        return results

    async def zrange(self, key, start, stop, withscores=False):
        items = sorted(self._zsets[key])
        if stop == -1:
            sliced = items[start:]
        else:
            sliced = items[start:stop + 1]
        if withscores:
            return [(m, s) for s, m in sliced]
        return [m for _, m in sliced]

    async def zremrangebyscore(self, key, min_score, max_score):
        before = len(self._zsets[key])
        self._zsets[key] = [
            (s, m) for s, m in self._zsets[key] if not (min_score <= s <= max_score)
        ]
        heapq.heapify(self._zsets[key])
        return before - len(self._zsets[key])

    async def zcard(self, key):
        return len(self._zsets[key])

    async def zrem(self, key, *members):
        before = len(self._zsets[key])
        self._zsets[key] = [(s, m) for s, m in self._zsets[key] if m not in members]
        heapq.heapify(self._zsets[key])
        return before - len(self._zsets[key])

    async def expire(self, key, seconds):
        return True

    async def aclose(self):
        pass


class FakePipeline:
    """Batches commands and executes them sequentially."""

    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._cmds = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._cmds.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zadd(self, key, mapping):
        self._cmds.append(("zadd", key, mapping))
        return self

    def zcard(self, key):
        self._cmds.append(("zcard", key))
        return self

    def expire(self, key, seconds):
        self._cmds.append(("expire", key, seconds))
        return self

    async def execute(self):
        results = []
        for cmd in self._cmds:
            op = cmd[0]
            if op == "zremrangebyscore":
                results.append(await self._redis.zremrangebyscore(cmd[1], cmd[2], cmd[3]))
            elif op == "zadd":
                results.append(await self._redis.zadd(cmd[1], cmd[2]))
            elif op == "zcard":
                results.append(await self._redis.zcard(cmd[1]))
            elif op == "expire":
                results.append(await self._redis.expire(cmd[1], cmd[2]))
        return results


# ---------------------------------------------------------------------------
# Build the FastAPI app (import after DB patch)
# ---------------------------------------------------------------------------
from app.api.routers import notifications, users
from app.api.dependencies import get_db, get_redis
from app.database import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create SQLite tables
    async with _sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("SQLite tables created")

    # wire fake redis onto app state
    app.state.redis = FakeRedis()
    logger.info("FakeRedis ready")

    # start worker
    from app.queue.worker import run_worker
    app.state.worker_task = asyncio.create_task(run_worker(app.state.redis))
    logger.info("Worker started")

    yield

    app.state.worker_task.cancel()
    await app.state.worker_task


app = FastAPI(
    title="Notification Service (Demo Mode)",
    description="Running with SQLite + FakeRedis — no external services needed",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "mode": "demo (SQLite + FakeRedis)"}


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Notification Service — DEMO MODE")
    print("  SQLite + FakeRedis (no Docker needed)")
    print("="*60)
    print("  Swagger UI  →  http://localhost:8000/docs")
    print("  Health      →  http://localhost:8000/health")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
