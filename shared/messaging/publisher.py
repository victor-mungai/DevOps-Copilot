import logging
from typing import Any, Dict, Optional

from .connection import get_messaging_manager
from .events import create_event, serialize_event

logger = logging.getLogger("messaging")


def publish(
    event_type: str,
    tenant_id: str,
    source: str,
    payload: Dict[str, Any],
    region: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    event_id: Optional[str] = None,
    retry_count: int = 0
) -> bool:
    """Publish standardized event envelope to RabbitMQ exchange."""
    event = create_event(
        event_type=event_type,
        tenant_id=tenant_id,
        source=source,
        payload=payload,
        region=region,
        resource_id=resource_id,
        resource_type=resource_type,
        event_id=event_id,
        retry_count=retry_count
    )
    serialized = serialize_event(event)
    manager = get_messaging_manager()
    success = manager.publish_message(routing_key=event_type, message_body=serialized)
    if success:
        logger.info("Published event %s [%s] for tenant %s", event_type, event.get("event_id"), tenant_id)
    else:
        logger.error("Failed to publish event %s for tenant %s", event_type, tenant_id)
    return success


publish_event = publish

