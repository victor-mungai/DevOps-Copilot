"""Canonical Resource Identity Service.

Resolves human-readable display names across EC2, RDS, EBS, and Lambda resources
following standard AWS tag priority: Name -> Application -> Service -> Environment + Type -> Resource ID.
"""
from typing import Any, Optional


def resolve_display_name(
    resource_id: str,
    resource_type: str,
    tags: Optional[dict] = None,
    raw_name: Optional[str] = None,
) -> str:
    tags = tags or {}

    # Priority 1-3: AWS Tags (Name -> Application -> Service)
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

    # Priority 4: Raw AWS identifier (DBInstanceIdentifier / FunctionName)
    if raw_name:
        return str(raw_name).strip()

    rtype = resource_type.upper()
    env = tags.get("Environment") or tags.get("environment")

    # Priority 5: Environment + Resource Type
    if env:
        return f"{env} {rtype}"

    # Priority 6: Resource ID
    return resource_id or f"{rtype} Resource"


def get_canonical_resource(
    resource_id: str,
    resource_type: str,
    tags: Optional[dict] = None,
    raw_name: Optional[str] = None,
    region: str = "us-east-2",
    account_id: Optional[str] = None,
) -> dict[str, Any]:
    display_name = resolve_display_name(resource_id, resource_type, tags=tags, raw_name=raw_name)
    return {
        "resource_id": resource_id,
        "display_name": display_name,
        "resource_type": resource_type.upper(),
        "account_id": account_id or "connected-aws-account",
        "region": region,
        "tags": tags or {},
    }
