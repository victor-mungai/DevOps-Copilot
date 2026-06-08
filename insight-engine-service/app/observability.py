"""Lightweight request context + structured logging (Feature 11).

A full structured-logging rollout across all services is Phase 2; here we give
the insight engine a request_id and a tenant-aware logger so every log line can
carry request_id / tenant_id / service / endpoint.
"""

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("insight-engine")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        # X-Tenant-ID is injected by the gateway tenant middleware.
        request.state.tenant_id = request.headers.get("X-Tenant-ID")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")
