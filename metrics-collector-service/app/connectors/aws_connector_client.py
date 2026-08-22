import os
from typing import Any

import requests

DEFAULT_CONNECTOR_BASE = "http://127.0.0.1:8000/v1/aws"


def _base_url() -> str:
    explicit = os.getenv("AWS_CONNECTOR_BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    direct = os.getenv("AWS_CONNECTOR_SERVICE_URL")
    if direct:
        return f"{direct.rstrip('/')}/aws"

    return DEFAULT_CONNECTOR_BASE


def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _request_json(method: str, url: str, **kwargs) -> dict[str, Any]:
    response = requests.request(method, url, timeout=30, **kwargs)
    try:
        payload = response.json()
    except ValueError as exc:
        body = response.text[:500] if response.text else "<empty body>"
        raise RuntimeError(
            f"AWS connector returned non-JSON response "
            f"({response.status_code}) for {url}: {body}"
        ) from exc

    if not response.ok:
        detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
        raise RuntimeError(
            f"AWS connector request failed ({response.status_code}) for {url}: {detail}"
        )

    return payload


def get_ec2_instances(tenant_id: str, region: str = None) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/ec2/instances"
    if region:
        url += f"?region={region}"
    return _unwrap(_request_json("GET", url))


def get_rds_instances(tenant_id: str, region: str = None) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/rds/databases"
    if region:
        url += f"?region={region}"
    return _unwrap(_request_json("GET", url))


def get_lambda_functions(tenant_id: str, region: str = None) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/lambda/functions"
    if region:
        url += f"?region={region}"
    return _unwrap(_request_json("GET", url))


def get_cloudwatch_metrics(tenant_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/cloudwatch/metrics"
    return _request_json("GET", url)


def get_cloudwatch_metric_statistics(
    tenant_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/cloudwatch/metric-statistics"
    return _request_json("POST", url, json=payload)
