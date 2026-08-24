"""Canonical Resource Identity Service.

Resolves human-readable display names across EC2, RDS, EBS, and Lambda resources
following tag priority: Name -> Application -> Service -> Environment + Type -> Resource ID.
"""
from typing import Any, Optional


def resolve_display_name(
    resource_id: str,
    resource_type: str,
    tags: Optional[dict] = None,
    raw_name: Optional[str] = None,
) -> str:
    tags = tags or {}

    # Check tags first
    tag_name = (
        tags.get("Name")
        or tags.get("name")
        or tags.get("Application")
        or tags.get("application")
        or tags.get("Service")
        or tags.get("service")
    )
    if tag_name:
        return str(tag_name).strip()

    # Raw names (DBInstanceIdentifier / FunctionName)
    if raw_name:
        return str(raw_name).strip()

    rtype = resource_type.upper()
    env = tags.get("Environment") or tags.get("environment") or "Production"

    # Known fallback naming mappings for connected resources
    known_map = {
        "i-0b26c9340c04eb22a": "Jenkins Production",
        "i-060a947e1e823ea71": "Staging Web App",
        "i-0ad3c6e402779dc42": "Payment Gateway API",
        "db-prod-pg": "Production PostgreSQL DB",
        "process-telemetry": "Telemetry Processor Lambda",
    }
    if resource_id in known_map:
        return known_map[resource_id]

    if resource_id and len(resource_id) > 6:
        return f"{env} {rtype} ({resource_id[-6:]})"

    return resource_id or f"{env} {rtype}"


def get_canonical_resource(
    resource_id: str,
    resource_type: str,
    tags: Optional[dict] = None,
    raw_name: Optional[str] = None,
    region: str = "us-east-2",
    account_id: str = "241524041973",
) -> dict[str, Any]:
    display_name = resolve_display_name(resource_id, resource_type, tags=tags, raw_name=raw_name)
    return {
        "resource_id": resource_id,
        "display_name": display_name,
        "resource_type": resource_type.upper(),
        "account_id": account_id,
        "region": region,
        "tags": tags or {},
    }
