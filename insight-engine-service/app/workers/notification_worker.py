import logging
import sys
import time
from typing import Any, Dict

sys.path.insert(0, ".")
sys.path.insert(0, "insight-engine-service")

from shared.messaging import EventConsumer, config as msg_config

logger = logging.getLogger("notification-worker")


def process_notification_job(event: Dict[str, Any]):
    tenant_id = event.get("tenant_id")
    payload = event.get("payload", {})
    insight = payload.get("insight", {})

    severity = (insight.get("severity") or payload.get("severity") or "info").lower()
    if severity in ("high", "critical"):
        issue = insight.get("issue") or payload.get("issue") or "Infrastructure Anomaly Detected"
        resource_id = insight.get("resource_id") or payload.get("resource_id") or "N/A"
        logger.info(
            "ALERT DISPATCHED [Severity: %s | Tenant: %s | Resource: %s]: %s",
            severity.upper(), tenant_id, resource_id, issue
        )


def start_worker():
    logger.info("Starting Notification Dispatch Background Worker...")
    consumer = EventConsumer(
        queue_name=msg_config.QUEUE_NOTIFICATIONS,
        handler=process_notification_job,
        prefetch_count=10
    )
    consumer.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_worker()
    while True:
        time.sleep(1)
