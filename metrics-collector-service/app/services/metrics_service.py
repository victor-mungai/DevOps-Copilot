import logging
from typing import Iterable

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


def _extract_ec2_instance_ids(payload: dict) -> list[str]:
    instance_ids = []
    for reservation in payload.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_id = instance.get("InstanceId")
            if instance_id:
                instance_ids.append(instance_id)
    return instance_ids


def _extract_rds_ids(payload: dict) -> list[str]:
    ids = []
    for item in payload.get("DBInstances", []):
        db_id = item.get("DBInstanceIdentifier")
        if db_id:
            ids.append(db_id)
    return ids


def _extract_lambda_names(payload: dict) -> list[str]:
    names = []
    for item in payload.get("Functions", []):
        name = item.get("FunctionName")
        if name:
            names.append(name)
    return names


def collect_for_tenant(tenant_id: str) -> list[Metric]:
    logger.info("Collecting metrics for tenant %s", tenant_id)

    ec2_payload = get_ec2_instances(tenant_id)
    rds_payload = get_rds_instances(tenant_id)
    lambda_payload = get_lambda_functions(tenant_id)

    ec2_ids = _extract_ec2_instance_ids(ec2_payload)
    rds_ids = _extract_rds_ids(rds_payload)
    lambda_names = _extract_lambda_names(lambda_payload)

    metrics: list[Metric] = []
    metrics.extend(collect_ec2_metrics(tenant_id, ec2_ids))
    metrics.extend(collect_rds_metrics(tenant_id, rds_ids))
    metrics.extend(collect_lambda_metrics(tenant_id, lambda_names))

    push_metrics(metrics)
    logger.info("Collected %s metrics for tenant %s", len(metrics), tenant_id)
    return metrics


def collect_for_tenants(tenant_ids: Iterable[str]) -> dict:
    results = {}
    for tenant_id in tenant_ids:
        metrics = collect_for_tenant(tenant_id)
        results[tenant_id] = len(metrics)
    return results
