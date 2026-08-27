import gc
import logging
import sys
import time
from typing import Any, Dict

# Ensure shared module is in sys.path
sys.path.insert(0, ".")

from shared.messaging import EventConsumer, publish, config as msg_config
from app.collectors import ec2_collector, lambda_collector, rds_collector
from app.connectors.aws_connector_client import get_aws_credentials
from app.connectors.prometheus_client import push_metrics
from app.connectors.storage import get_metrics_storage

logger = logging.getLogger("metrics-worker")


def process_collection_job(event: Dict[str, Any]):
    tenant_id = event.get("tenant_id")
    region = event.get("region")
    payload = event.get("payload", {})
    resource_id = payload.get("resource_id") or event.get("resource_id")
    resource_type = payload.get("resource_type") or event.get("resource_type") or "ec2"

    logger.info("Processing metrics collection job for tenant %s, resource %s (%s)", tenant_id, resource_id, resource_type)

    if not tenant_id or not resource_id or not region:
        logger.warning("Invalid collection job payload: missing tenant_id, resource_id, or region")
        return

    # Obtain AWS credentials
    creds = get_aws_credentials(tenant_id)
    if not creds or "access_key_id" not in creds:
        logger.error("Failed to obtain AWS credentials for tenant %s", tenant_id)
        return

    access_key = creds["access_key_id"]
    secret_key = creds["secret_access_key"]
    session_token = creds.get("session_token")
    aws_account_id = creds.get("aws_account_id")
    if not aws_account_id:
        logger.error("AWS account id missing from credentials for tenant %s", tenant_id)
        return

    samples = []
    if resource_type == "ec2":
        samples = ec2_collector.collect(
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            instance_id=resource_id,
            session_token=session_token,
            tenant_id=tenant_id
        )
    elif resource_type == "rds":
        samples = rds_collector.collect(
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            db_identifier=resource_id,
            session_token=session_token,
            tenant_id=tenant_id
        )
    elif resource_type == "lambda":
        samples = lambda_collector.collect(
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            function_name=resource_id,
            session_token=session_token,
            tenant_id=tenant_id
        )

    if samples:
        storage = get_metrics_storage()
        push_metrics(samples, storage=storage, tenant_id=tenant_id, aws_account_id=aws_account_id, region=region)
        logger.info("Pushed %d metric samples for %s to storage", len(samples), resource_id)

    gc.collect()

    publish(
        event_type="metrics.collection.completed",
        tenant_id=tenant_id,
        source="metrics-worker",
        region=region,
        resource_id=resource_id,
        resource_type=resource_type,
        payload={"sample_count": len(samples)}
    )


def start_worker():
    logger.info("Starting Metrics Collection Background Worker...")
    consumer = EventConsumer(
        queue_name=msg_config.QUEUE_METRICS,
        handler=process_collection_job,
        prefetch_count=10
    )
    consumer.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_worker()
    while True:
        time.sleep(1)
