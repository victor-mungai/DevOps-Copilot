import gc
import logging
import os
from typing import Iterable

from .dispatcher import CollectionJob, get_dispatcher
from ..collectors.ec2_collector import collect_ec2_metrics
from ..collectors.lambda_collector import collect_lambda_metrics
from ..collectors.rds_collector import collect_rds_metrics
from ..connectors.aws_connector_client import (
    get_ec2_instances,
    get_lambda_functions,
    get_rds_instances,
)
from ..connectors.prometheus_client import push_metrics
from ..models.metric_schema import Metric

logger = logging.getLogger("metrics-collector")

MAX_CONCURRENT_RESOURCES = int(os.getenv("MAX_CONCURRENT_RESOURCES", "10"))


def _unwrap_payload(payload: dict) -> dict:
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


def _extract_ec2_instance_ids(payload: dict) -> list[str]:
    data = _unwrap_payload(payload)
    instance_ids = []
    for reservation in data.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_id = instance.get("InstanceId")
            if instance_id:
                instance_ids.append(instance_id)
    return instance_ids


def _extract_rds_ids(payload: dict) -> list[str]:
    data = _unwrap_payload(payload)
    ids = []
    for item in data.get("DBInstances", []):
        db_id = item.get("DBInstanceIdentifier")
        if db_id:
            ids.append(db_id)
    return ids


def _extract_lambda_names(payload: dict) -> list[str]:
    data = _unwrap_payload(payload)
    names = []
    for item in data.get("Functions", []):
        name = item.get("FunctionName")
        if name:
            names.append(name)
    return names


def _batch_list(items: list, batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def collect_for_tenant(tenant_id: str, region: str = None) -> list[Metric]:
    logger.info("Collecting metrics for tenant %s in region %s", tenant_id, region or "default")
    total_metrics: list[Metric] = []
    try:
        # 1. Discover Resources
        ec2_payload = get_ec2_instances(tenant_id, region=region)
        rds_payload = get_rds_instances(tenant_id, region=region)
        lambda_payload = get_lambda_functions(tenant_id, region=region)

        ec2_ids = _extract_ec2_instance_ids(ec2_payload)
        rds_ids = _extract_rds_ids(rds_payload)
        lambda_names = _extract_lambda_names(lambda_payload)

        # 2. Incremental Batching & Streaming Processing (EC2)
        for ec2_batch in _batch_list(ec2_ids, MAX_CONCURRENT_RESOURCES):
            batch_metrics = collect_ec2_metrics(tenant_id, ec2_batch, region=region)
            if batch_metrics:
                push_metrics(batch_metrics)
                total_metrics.extend(batch_metrics)
            gc.collect()

        # 3. Incremental Batching & Streaming Processing (RDS)
        for rds_batch in _batch_list(rds_ids, MAX_CONCURRENT_RESOURCES):
            batch_metrics = collect_rds_metrics(tenant_id, rds_batch, region=region)
            if batch_metrics:
                push_metrics(batch_metrics)
                total_metrics.extend(batch_metrics)
            gc.collect()

        # 4. Incremental Batching & Streaming Processing (Lambda)
        for lambda_batch in _batch_list(lambda_names, MAX_CONCURRENT_RESOURCES):
            batch_metrics = collect_lambda_metrics(tenant_id, lambda_batch, region=region)
            if batch_metrics:
                push_metrics(batch_metrics)
                total_metrics.extend(batch_metrics)
            gc.collect()

        logger.info("Successfully collected and pushed %s metrics in batches for tenant %s", len(total_metrics), tenant_id)
        return total_metrics
    except Exception as exc:
        logger.warning("Metrics collection failed for tenant %s: %s", tenant_id, exc)
        return []


def collect_for_tenants(tenant_ids: Iterable[str]) -> dict:
    results = {}
    dispatcher = get_dispatcher()
    for tenant_id in tenant_ids:
        job = CollectionJob(tenant_id=tenant_id)
        dispatcher.dispatch(job, lambda j: results.update({j.tenant_id: len(collect_for_tenant(j.tenant_id))}))
    return results
