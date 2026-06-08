from typing import Any

import requests

from .. import config


def _base_url() -> str:
    if config.AWS_CONNECTOR_BASE_URL:
        return config.AWS_CONNECTOR_BASE_URL.rstrip("/")
    if config.AWS_CONNECTOR_SERVICE_URL:
        return f"{config.AWS_CONNECTOR_SERVICE_URL.rstrip('/')}/aws"
    return config.DEFAULT_CONNECTOR_BASE


def get_ec2_instances(tenant_id: str) -> dict[str, Any]:
    assert tenant_id, "tenant_id is required"
    url = f"{_base_url()}/{tenant_id}/ec2/instances"
    resp = requests.get(url, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def list_ec2_instances(tenant_id: str) -> list[dict]:
    payload = get_ec2_instances(tenant_id)
    body = payload.get("data", payload) if isinstance(payload, dict) else {}
    instances: list[dict] = []
    for reservation in body.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_id = instance.get("InstanceId")
            if not instance_id:
                continue
            instances.append(
                {
                    "instance_id": instance_id,
                    "instance_type": instance.get("InstanceType"),
                }
            )
    return instances
