from __future__ import annotations

import logging
import time

from fastapi import Cookie, Header, HTTPException, Request, status

from .auth import decode_access_token
from .config import settings
from .redis_client import get_redis

logger = logging.getLogger("spiritualized.ratelimit")


def _client_ip(request: Request) -> str:
    # Railway/Vercel sit behind a proxy, so trust the first X-Forwarded-For hop when present.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(identifier: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Fixed-window counter. Returns (allowed, retry_after_seconds).

    Fails open (allows) when Redis is unconfigured or errors, so an Upstash hiccup never takes
    down chat — the limiter is a cost guard, not a hard gate.
    """
    redis = get_redis()
    if redis is None:
        return True, 0

    now = int(time.time())
    window_id = now // window_seconds
    key = f"rl:{identifier}:{window_id}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > limit:
            return False, window_seconds - (now % window_seconds)
        return True, 0
    except Exception as exc:
        logger.warning("Rate limit check failed (fail-open): %s", exc)
        return True, 0


async def rate_limit_chat(
    request: Request,
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Per-user (or per-IP for anonymous) guard, applied before each LLM call to cap token spend."""
    if not settings.RATE_LIMIT_ENABLED:
        return

    token = access_token
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()

    user_id = None
    if token:
        data = decode_access_token(token)
        if data:
            user_id = data.user_id

    identifier = f"user:{user_id}" if user_id else f"ip:{_client_ip(request)}"
    allowed, retry_after = await check_rate_limit(
        identifier, settings.CHAT_RATE_LIMIT, settings.RATE_LIMIT_WINDOW_SECONDS
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down and try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
