from __future__ import annotations

import logging

from upstash_redis.asyncio import Redis

from .config import settings

logger = logging.getLogger("spiritualized.redis")

_redis: Redis | None = None


def get_redis() -> Redis | None:
    """Lazy singleton Upstash client. Returns None when creds are unset (limiter no-ops)."""
    global _redis
    if _redis is None:
        if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
            return None
        _redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.close()
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logger.warning("Error closing Redis client: %s", exc)
        _redis = None
