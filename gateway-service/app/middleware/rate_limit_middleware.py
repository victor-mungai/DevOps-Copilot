import os
import time
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
WINDOW_SECONDS = 60

_store = {}
_lock = Lock()


def _key(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return f"tenant:{tenant_id}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


async def rate_limit_middleware(request: Request, call_next):
    if os.getenv("RATE_LIMIT_DISABLED", "false").lower() == "true":
        return await call_next(request)

    key = _key(request)
    now = time.time()

    with _lock:
        window_start, count = _store.get(key, (now, 0))
        if now - window_start >= WINDOW_SECONDS:
            window_start, count = now, 0
        count += 1
        _store[key] = (window_start, count)

        if count > RATE_LIMIT_PER_MINUTE:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

    return await call_next(request)
