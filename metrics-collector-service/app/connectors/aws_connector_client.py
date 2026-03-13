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


def get_ec2_instances(tenant_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/ec2/instances"
    return requests.get(url, timeout=30).json()


def get_rds_instances(tenant_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/rds/databases"
    return requests.get(url, timeout=30).json()


def get_lambda_functions(tenant_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/lambda/functions"
    return requests.get(url, timeout=30).json()


def get_cloudwatch_metrics(tenant_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/cloudwatch/metrics"
    return requests.get(url, timeout=30).json()


def get_cloudwatch_metric_statistics(
    tenant_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    url = f"{_base_url()}/{tenant_id}/cloudwatch/metric-statistics"
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()
