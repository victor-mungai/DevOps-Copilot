"""Tenant-scoped Prometheus query proxy.

The client never sends raw PromQL. We build the selector server-side from the
authenticated tenant plus a whitelisted metric name, so a tenant can only ever
read its own series. Label values are validated to prevent PromQL injection.
"""
import os
import re
import time

import httpx
from fastapi import HTTPException

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090").rstrip("/")

# Whitelisted metric keys -> Prometheus metric names. Only cpu has data today;
# the others resolve to plausible names that simply return empty series until
# the collector emits them (the UI renders an honest empty state).
METRIC_MAP = {
    "cpu": os.getenv("METRIC_NAME_CPU", "cpu_utilization"),
    "memory": os.getenv("METRIC_NAME_MEMORY", "memory_utilization"),
    "network": os.getenv("METRIC_NAME_NETWORK", "network_bytes_total"),
    "disk": os.getenv("METRIC_NAME_DISK", "disk_utilization"),
}

LABEL_TENANT = os.getenv("PROM_LABEL_TENANT", "tenant")
LABEL_RESOURCE = os.getenv("PROM_LABEL_RESOURCE", "resource")

# Tenant ids (UUID) and AWS resource ids are alphanumeric + - _ . only.
_SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe(value: str, field: str) -> str:
    if not _SAFE.match(value):
        raise HTTPException(status_code=400, detail=f"invalid {field}")
    return value


async def query_range(
    tenant_id: str,
    metric: str,
    resource: str | None,
    minutes: int,
    step: int,
) -> dict:
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    _safe(tenant_id, "tenant_id")

    name = METRIC_MAP.get(metric)
    if not name:
        raise HTTPException(status_code=400, detail=f"unknown metric '{metric}'")

    selector = f'{name}{{{LABEL_TENANT}="{tenant_id}"'
    if resource:
        _safe(resource, "resource")
        selector += f',{LABEL_RESOURCE}="{resource}"'
    selector += "}"

    minutes = max(5, min(int(minutes), 7 * 24 * 60))  # clamp 5m .. 7d
    step = max(15, min(int(step), 3600))  # clamp 15s .. 1h
    end = time.time()
    start = end - minutes * 60

    url = f"{PROMETHEUS_URL}/api/v1/query_range"
    params = {"query": selector, "start": start, "end": end, "step": step}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Prometheus query failed: {exc}") from exc

    body = resp.json()
    return {
        "metric": metric,
        "metric_name": name,
        "resource": resource or None,
        "result": body.get("data", {}).get("result", []),
    }
