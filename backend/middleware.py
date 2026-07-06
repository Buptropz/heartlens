import time
from collections import defaultdict
from fastapi import Request, HTTPException
from config import settings

_window_requests: dict[str, list[float]] = defaultdict(list)


async def rate_limit_dependency(request: Request):
    """FastAPI dependency for rate limiting by client IP."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 3600  # 1 hour

    # Remove old entries
    _window_requests[ip] = [t for t in _window_requests[ip] if t > window_start]

    if len(_window_requests[ip]) >= settings.rate_limit_per_hour:
        raise HTTPException(
            429,
            detail={"error": "rate_limited", "retry_after": 3600},
        )

    _window_requests[ip].append(now)
