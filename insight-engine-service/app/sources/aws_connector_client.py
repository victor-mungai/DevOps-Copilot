from typing import Any

import requests

from .. import config


class ConnectorError(RuntimeError):
    """Raised when the aws-connector dependency is unreachable or errors.

    Lets callers distinguish an upstream-dependency failure (map to 502) from a
    genuine internal bug (500).
    """


def _base_url() -> str:
    if config.AWS_CONNECTOR_BASE_URL:
        return config.AWS_CONNECTOR_BASE_URL.rstrip("/")
    if config.AWS_CONNECTOR_SERVICE_URL:
        return f"{config.AWS_CONNECTOR_SERVICE_URL.rstrip('/')}/aws"
    return config.DEFAULT_CONNECTOR_BASE


def _with_region(url: str, region: str | None) -> str:
    if region:
        connector = "&" if "?" in url else "?"
        return f"{url}{connector}region={requests.utils.quote(region)}"
    return url


def get_ec2_instances(tenant_id: str, region: str | None = None) -> dict[str, Any]:
    assert tenant_id, "tenant_id is required"
    url = _with_region(f"{_base_url()}/{tenant_id}/ec2/instances", region)
    try:
        resp = requests.get(url, timeout=0.5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return {}


def list_ec2_instances(tenant_id: str, region: str | None = None) -> list[dict]:
    try:
        payload = get_ec2_instances(tenant_id, region=region)
        body = payload.get("data", payload) if isinstance(payload, dict) else {}
        instances: list[dict] = []
        for reservation in body.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId")
                if not instance_id:
                    continue
                tags = {
                    t.get("Key", "").strip(): t.get("Value", "")
                    for t in instance.get("Tags", [])
                    if t.get("Key")
                }
                instances.append(
                    {
                        "instance_id": instance_id,
                        "instance_type": instance.get("InstanceType"),
                        "tags": tags,
                        "state": (instance.get("State") or {}).get("Name"),
                        "region": (instance.get("Placement") or {}).get("AvailabilityZone"),
                    }
                )
        return instances
    except Exception:
        return []


def get_rds_databases(tenant_id: str, region: str | None = None) -> dict[str, Any]:
    assert tenant_id, "tenant_id is required"
    url = _with_region(f"{_base_url()}/{tenant_id}/rds/databases", region)
    try:
        resp = requests.get(url, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        return {}


def list_rds_databases(tenant_id: str, region: str | None = None) -> list[dict]:
    payload = get_rds_databases(tenant_id, region=region)
    body = payload.get("data", payload) if isinstance(payload, dict) else {}
    dbs: list[dict] = []
    for item in body.get("DBInstances", []):
        db_id = item.get("DBInstanceIdentifier")
        if db_id:
            dbs.append({
                "resource_id": db_id,
                "engine": item.get("Engine"),
                "status": item.get("DBInstanceStatus"),
                "free_storage_gb": item.get("AllocatedStorage", 100),
            })
    return dbs


def get_lambda_functions(tenant_id: str, region: str | None = None) -> dict[str, Any]:
    assert tenant_id, "tenant_id is required"
    url = _with_region(f"{_base_url()}/{tenant_id}/lambda/functions", region)
    try:
        resp = requests.get(url, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        return {}


def list_lambda_functions(tenant_id: str, region: str | None = None) -> list[dict]:
    payload = get_lambda_functions(tenant_id, region=region)
    body = payload.get("data", payload) if isinstance(payload, dict) else {}
    fns: list[dict] = []
    for item in body.get("Functions", []):
        name = item.get("FunctionName")
        if name:
            fns.append({
                "resource_id": name,
                "runtime": item.get("Runtime"),
                "memory_mb": item.get("MemorySize"),
            })
    return fns
