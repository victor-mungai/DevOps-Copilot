import os

from fastapi import Request
from fastapi.responses import Response
import httpx

from ..middleware.tenant_middleware import get_tenant_headers
from ..config.service_registry import get_service_url

HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _filter_headers(headers: dict) -> dict:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_HEADERS}


async def proxy_request_to(url: str, request: Request, inject_tenant: bool = True) -> Response:
    method = request.method
    headers = _filter_headers(dict(request.headers))

    if inject_tenant:
        headers.update(get_tenant_headers(request))

    body = await request.body()

    timeout = float(os.getenv("FORWARD_TIMEOUT", "30"))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.request(method, url, headers=headers, content=body, params=request.query_params)

    resp_headers = _filter_headers(dict(resp.headers))
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
        media_type=resp.headers.get("content-type"),
    )


async def forward_request(service: str, path: str, request: Request, inject_tenant: bool = True) -> Response:
    base = get_service_url(service)
    url = f"{base}{path}"
    return await proxy_request_to(url, request, inject_tenant=inject_tenant)
