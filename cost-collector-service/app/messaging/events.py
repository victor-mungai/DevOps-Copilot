import logging
from shared.messaging.events import create_event, EVENT_COST_COLLECTION_REQUESTED
from shared.messaging.publisher import publish

logger = logging.getLogger("cost-collector")


def request_cost_collection(tenant_id: str, region: str = "us-east-2", period: str = "30d") -> dict:
    event = create_event(
        event_type=EVENT_COST_COLLECTION_REQUESTED,
        tenant_id=tenant_id,
        source="cost-collector-api",
        region=region,
        payload={"period": period, "region": region},
    )
    published = publish(
        event_type=EVENT_COST_COLLECTION_REQUESTED,
        tenant_id=tenant_id,
        source="cost-collector-api",
        region=region,
        payload={"period": period, "region": region},
    )
    if published:
        logger.info("Published cost.collection.requested event for tenant %s", tenant_id)
    return event
