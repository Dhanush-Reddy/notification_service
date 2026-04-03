import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routers import notifications, users

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Redis connected")

    # run migrations on startup — fine for demo; in prod use a proper migration job
    from alembic import command as alembic_cmd
    from alembic.config import Config as AlembicConfig
    alembic_cfg = AlembicConfig("alembic.ini")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, alembic_cmd.upgrade, alembic_cfg, "head")
    logger.info("DB migrations applied")

    from app.queue.worker import run_worker
    app.state.worker_task = asyncio.create_task(run_worker(app.state.redis))
    logger.info("Notification worker started")

    yield

    # --- shutdown ---
    worker_task = getattr(app.state, "worker_task", None)
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    redis = getattr(app.state, "redis", None)
    if redis:
        await redis.aclose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Notification Service",
        description="Multi-channel notification delivery service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
    app.include_router(users.router, prefix="/users", tags=["users"])

    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
