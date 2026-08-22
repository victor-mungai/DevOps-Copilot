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

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://18.116.65.134:9090").rstrip("/")

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

# Tenant ids (UUID) and AWS resource ids (including ARNs) permit colons, slashes, etc.
_SAFE = re.compile(r"^[A-Za-z0-9._\-:/ ]+$")


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

    minutes = max(5, min(int(minutes), 30 * 24 * 60))  # clamp 5m .. 30d
    step = max(15, min(int(step), 86400))  # clamp 15s .. 24h
    end = time.time()
    start = end - minutes * 60

    prom_url = os.getenv("PROMETHEUS_URL", PROMETHEUS_URL).rstrip("/")
    url = f"{prom_url}/api/v1/query_range"
    params = {"query": selector, "start": start, "end": end, "step": step}
    result = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                result = resp.json().get("data", {}).get("result", [])

            # Fall back to instant query if range query returned empty series
            if not result:
                instant_url = f"{prom_url}/api/v1/query"
                i_resp = await client.get(instant_url, params={"query": selector})
                if i_resp.status_code == 200:
                    i_result = i_resp.json().get("data", {}).get("result", [])
                    if i_result:
                        for item in i_result:
                            val_pair = item.get("value")
                            if val_pair and len(val_pair) == 2:
                                ts, val = float(val_pair[0]), val_pair[1]
                                synthesized_values = [
                                    [ts - step, val],
                                    [ts, val],
                                ]
                                result.append({
                                    "metric": item.get("metric", {}),
                                    "values": synthesized_values,
                                })

            # Trigger background on-demand metric collection if result is still empty
            if not result:
                collector_url = os.getenv("METRICS_COLLECTOR_SERVICE_URL", "http://127.0.0.1:8004")
                try:
                    await client.post(f"{collector_url}/collect/tenant/{tenant_id}", timeout=2.0)
                except Exception:
                    pass

    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Prometheus query failed: {exc}") from exc

    return {
        "metric": metric,
        "metric_name": name,
        "resource": resource or None,
        "result": result,
    }
