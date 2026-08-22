from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, Optional


def create_event(
    event_type: str,
    tenant_id: str,
    source: str,
    payload: Dict[str, Any],
    region: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    event_id: Optional[str] = None,
    retry_count: int = 0
) -> Dict[str, Any]:
    """Construct standard event envelope."""
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "region": region or "us-east-2",
        "source": source,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "retry_count": retry_count,
        "payload": payload or {}
    }


def serialize_event(event: Dict[str, Any]) -> str:
    """Serialize event dictionary to JSON string."""
    return json.dumps(event)


def deserialize_event(data: str) -> Dict[str, Any]:
    """Deserialize JSON string into event dictionary."""
    return json.loads(data)
