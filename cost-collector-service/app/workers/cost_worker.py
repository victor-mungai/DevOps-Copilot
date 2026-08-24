import logging
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from shared.messaging.config import QUEUE_COST, DLQ_COST
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import EVENT_COST_COLLECTION_REQUESTED
from ..db.connection import SessionLocal
from ..services.cost_collection import ingest_cost_records

logger = logging.getLogger("cost-worker")
logging.basicConfig(level=logging.INFO)


def process_cost_event(event: dict) -> bool:
    event_type = event.get("event_type")
    tenant_id = event.get("tenant_id")
    if not tenant_id:
        return True

    if event_type == EVENT_COST_COLLECTION_REQUESTED:
        logger.info("Processing cost collection job for tenant %s", tenant_id)
        db = SessionLocal()
        try:
            ingest_cost_records(db, tenant_id, days=90)
            logger.info("Cost collection job completed successfully for tenant %s", tenant_id)
            return True
        except Exception as exc:
            logger.exception("Error processing cost collection job for tenant %s: %s", tenant_id, exc)
            return False
        finally:
            db.close()
    return True


def start_cost_worker():
    logger.info("Starting Cost Collector Background Worker...")
    consumer = EventConsumer(queue_name=QUEUE_COST, handler=process_cost_event)
    consumer.start()


if __name__ == "__main__":
    start_cost_worker()
