import os

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse


def _is_exempt_path(path: str) -> bool:
    raw = os.getenv(
        "AUTH_EXEMPT_PATHS",
        "/v1/tenants,/docs,/openapi.json,/health,/v1/health,/",  # allow base path for UI proxy
    )
    prefixes = [p.strip() for p in raw.split(",") if p.strip()]
    for p in prefixes:
        if p.endswith("/*"):
            if path.startswith(p[:-1]):
                return True
        elif path == p:
            return True
    return False


def _get_token(header: str) -> str:
    if not header:
        return ""
    if header.lower().startswith("bearer "):
        return header[7:]
    return header


def _decode_token(token: str) -> dict:
    secret = os.getenv("JWT_SECRET", "dev-secret")
    algorithms = [os.getenv("JWT_ALGORITHM", "HS256")]
    return jwt.decode(token, secret, algorithms=algorithms)


async def auth_middleware(request: Request, call_next):
    if _is_exempt_path(request.url.path):
        return await call_next(request)

    if os.getenv("AUTH_DISABLED", "true").lower() == "true":
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            request.state.tenant_id = tenant_id
        return await call_next(request)

    token = _get_token(request.headers.get("Authorization", ""))
    if not token:
        return JSONResponse({"detail": "missing token"}, status_code=401)

    try:
        payload = _decode_token(token)
    except Exception:
        return JSONResponse({"detail": "invalid token"}, status_code=401)

    request.state.tenant_id = payload.get("tenant_id")
    request.state.user_id = payload.get("user_id")
    request.state.roles = payload.get("roles")

    return await call_next(request)
