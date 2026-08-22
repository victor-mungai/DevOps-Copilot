import logging
import sys
import time
from typing import Any, Dict

sys.path.insert(0, ".")
sys.path.insert(0, "insight-engine-service")

from shared.messaging import EventConsumer, config as msg_config
from app.db.connection import SessionLocal
from app.db import insight_repository
from app.services import rag_service

logger = logging.getLogger("rag-worker")


def process_rag_job(event: Dict[str, Any]):
    tenant_id = event.get("tenant_id")
    region = event.get("region", "us-east-2")
    payload = event.get("payload", {})
    insight_record = payload.get("insight")
    insight_id = payload.get("insight_id")

    logger.info("Processing RAG ingestion job for tenant %s (insight_id=%s)", tenant_id, insight_id)

    if not tenant_id:
        return

    if not insight_record and insight_id:
        db = SessionLocal()
        try:
            stored = insight_repository.get_insight(db, insight_id)
            if stored:
                insight_record = stored.to_dict()
        finally:
            db.close()

    if insight_record:
        rag_service.index_insight(insight_record, region=region)
        logger.info("Indexed insight %s into Pinecone namespace %s", insight_id or insight_record.get("id"), tenant_id)


def start_worker():
    logger.info("Starting RAG Ingestion Background Worker...")
    consumer = EventConsumer(
        queue_name=msg_config.QUEUE_RAG,
        handler=process_rag_job,
        prefetch_count=10
    )
    consumer.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_worker()
    while True:
        time.sleep(1)
