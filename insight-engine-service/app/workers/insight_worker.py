from datetime import datetime
import logging
import sys
import time
from typing import Any, Dict

sys.path.insert(0, ".")
sys.path.insert(0, "insight-engine-service")

from shared.messaging import EventConsumer, publish, config as msg_config
from app.db.connection import SessionLocal
from app.db import insight_repository
from app.db.models import Job
from app.services.analysis_service import analyze_tenant

logger = logging.getLogger("insight-worker")


def process_analysis_job(event: Dict[str, Any]):
    tenant_id = event.get("tenant_id")
    region = event.get("region", "us-east-2")
    payload = event.get("payload", {})
    job_id = payload.get("job_id")

    logger.info("Processing background analysis job %s for tenant %s (region=%s)", job_id, tenant_id, region)

    if not tenant_id:
        logger.warning("Invalid analysis event: missing tenant_id")
        return

    db = SessionLocal()
    try:
        # Update Job status to 'running'
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "running"
                job.started_at = datetime.utcnow()
                job.attempts += 1
                db.commit()

        # Execute rule engine
        insights = analyze_tenant(db=db, tenant_id=tenant_id, region=region)

        # Update Job status to 'completed'
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "completed"
                job.insights_found = len(insights)
                job.completed_at = datetime.utcnow()
                db.commit()

        # Emit insight.created event for each insight
        for record in insights:
            publish(
                event_type="insight.created",
                tenant_id=tenant_id,
                source="insight-worker",
                region=region,
                resource_id=record.get("resource_id"),
                resource_type=record.get("resource_type"),
                payload={"insight": record, "insight_id": record.get("id")}
            )

        logger.info("Background analysis job %s completed with %d insights", job_id, len(insights))
    except Exception as exc:
        db.rollback()
        logger.error("Analysis job %s failed: %s", job_id, exc)
        if job_id:
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                pass
        raise
    finally:
        db.close()


def start_worker():
    logger.info("Starting Insight Engine Background Worker...")
    consumer = EventConsumer(
        queue_name=msg_config.QUEUE_INSIGHTS,
        handler=process_analysis_job,
        prefetch_count=5
    )
    consumer.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_worker()
    while True:
        time.sleep(1)
