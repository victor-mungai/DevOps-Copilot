"""Canonical Resource Identity Service.

Resolves human-readable display names across EC2, RDS, EBS, and Lambda resources
following AWS-source-of-truth priority: Name tag -> raw AWS identifier -> resource ID.
"""
from typing import Any, Optional


def resolve_display_name(
    resource_id: str,
    resource_type: str,
    tags: Optional[dict] = None,
    raw_name: Optional[str] = None,
) -> str:
    tags = tags or {}

    tag_name = tags.get("Name") or tags.get("name")
    if tag_name:
        return str(tag_name).strip()

    # Priority 4: Raw AWS identifier (DBInstanceIdentifier / FunctionName)
    if raw_name:
        return str(raw_name).strip()

    return resource_id


def get_canonical_resource(
    resource_id: str,
    resource_type: str,
    tags: Optional[dict] = None,
    raw_name: Optional[str] = None,
    region: Optional[str] = None,
    account_id: Optional[str] = None,
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
