"""
Simple in-memory sliding-window rate limiter, scoped per authenticated
user_id, applied only to the chat endpoints (the ones that cost real
money via AI provider calls — conversation CRUD is cheap and unthrottled).

LIMITATION (documented, not hidden): this is per-process in-memory state.
It works correctly for a single backend instance. If you scale to
multiple backend instances behind a load balancer, replace the dict
below with a shared store (Redis is the standard choice) — the function
signature and call site don't need to change, only what's inside _hits.
"""
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user_id
from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# user_id -> deque of request timestamps (seconds)
_hits: dict[str, deque] = defaultdict(deque)


async def rate_limit_chat(user_id: str = Depends(get_current_user_id)) -> str:
    settings = get_settings()
    limit = settings.chat_rate_limit_requests
    window = settings.chat_rate_limit_window_seconds

    now = time.monotonic()
    hits = _hits[user_id]

    while hits and now - hits[0] > window:
        hits.popleft()

    if len(hits) >= limit:
        retry_after = max(1, int(window - (now - hits[0])))
        logger.warning("Rate limit exceeded for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You're sending messages too quickly. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
        )

    hits.append(now)
    return user_id
