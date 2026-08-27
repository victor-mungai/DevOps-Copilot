import os
from datetime import datetime, timedelta
from typing import Iterable, Optional

from ..connectors.aws_connector_client import get_cloudwatch_metric_statistics
from ..models.metric_schema import Metric

DEFAULT_REGION = os.getenv("DEFAULT_METRICS_REGION")
HISTORICAL_PERIOD_SECONDS = 900


def _fetch_rds_stat(
    tenant_id: str,
    region: str,
    metric_name: str,
    db_id: str,
    stat: str,
    end_time: datetime,
    account_id: str | None = None,
) -> Optional[float]:
    payload = {
        "namespace": "AWS/RDS",
        "metric_name": metric_name,
        "dimensions": [{"Name": "DBInstanceIdentifier", "Value": db_id}],
        "start_time": (end_time - timedelta(days=14)).isoformat(),
        "end_time": end_time.isoformat(),
        "period": HISTORICAL_PERIOD_SECONDS,
        "statistics": [stat],
        "region": region,
    }
    try:
        response = get_cloudwatch_metric_statistics(tenant_id, payload, account_id=account_id)
        datapoints = response.get("data", {}).get("Datapoints", [])
        if not datapoints:
            return None
        latest = sorted(datapoints, key=lambda x: x.get("Timestamp", ""), reverse=True)[0]
        return float(latest.get(stat, 0.0))
    except Exception:
        return None


def _resource_parts(resource) -> tuple[str, str | None, str | None]:
    if isinstance(resource, dict):
        return resource.get("resource_id"), resource.get("aws_account_id"), resource.get("region")
    return str(resource), None, None


def collect_rds_metrics(
    tenant_id: str, db_ids: Iterable, region: str = None
) -> list[Metric]:
    metrics = []
    end_time = datetime.utcnow()
    iso_now = end_time.isoformat()

    for resource in db_ids:
        db_id, account_id, resource_region = _resource_parts(resource)
        metric_region = region or resource_region or DEFAULT_REGION
        if not db_id or not account_id or not metric_region:
            continue
        # 1. CPU Utilization
        cpu_val = _fetch_rds_stat(tenant_id, metric_region, "CPUUtilization", db_id, "Average", end_time, account_id)
        if cpu_val is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=db_id,
                    metric_name="cpu_utilization",
                    timestamp=iso_now,
                    value=round(cpu_val, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="rds",
                    labels={"resource_type": "rds", "stat": "Average"},
                )
            )

        # 2. Network Throughput
        net_rx = _fetch_rds_stat(tenant_id, metric_region, "NetworkReceiveThroughput", db_id, "Average", end_time, account_id) or 0.0
        net_tx = _fetch_rds_stat(tenant_id, metric_region, "NetworkTransmitThroughput", db_id, "Average", end_time, account_id) or 0.0
        if net_rx + net_tx > 0:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=db_id,
                    metric_name="network_bytes_total",
                    timestamp=iso_now,
                    value=round(net_rx + net_tx, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="rds",
                    labels={"resource_type": "rds", "stat": "Average"},
                )
            )

        # 3. Disk / Storage Space (FreeStorageSpace in Bytes)
        free_storage = _fetch_rds_stat(tenant_id, metric_region, "FreeStorageSpace", db_id, "Average", end_time, account_id)
        if free_storage is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=db_id,
                    metric_name="free_storage_bytes",
                    timestamp=iso_now,
                    value=round(free_storage, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="rds",
                    labels={"resource_type": "rds", "stat": "Average"},
                )
            )

        # 4. Memory (FreeableMemory in bytes, only when CloudWatch returns it)
        free_mem = _fetch_rds_stat(tenant_id, metric_region, "FreeableMemory", db_id, "Average", end_time, account_id)
        if free_mem is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=db_id,
                    metric_name="freeable_memory_bytes",
                    timestamp=iso_now,
                    value=round(free_mem, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="rds",
                    labels={"resource_type": "rds", "stat": "Average"},
                )
            )

    return metrics
