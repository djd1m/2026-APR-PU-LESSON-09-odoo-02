"""FastAPI AI service entry point for СтройУправ."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import estimate, health
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)


def _validate_required_env_vars() -> None:
    """Crash early if critical env vars are missing or empty."""
    required = ("AI_BASE_URL", "AI_API_KEY", "DATABASE_URL")
    missing = [name for name in required if not getattr(settings, name, None)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared resources on startup, tear down on shutdown."""
    # --- startup ---
    _validate_required_env_vars()

    app.state.ai_client = AIClient(settings)
    logger.info("AI client initialised (model=%s)", settings.AI_MODEL)

    app.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    logger.info("Redis connection pool created")

    yield

    # --- shutdown ---
    await app.state.redis.aclose()
    logger.info("Redis connection closed")


app = FastAPI(
    title="СтройУправ AI Service",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — configurable via ALLOWED_ORIGINS env var (comma-separated).
# Default: allow all during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(estimate.router)
