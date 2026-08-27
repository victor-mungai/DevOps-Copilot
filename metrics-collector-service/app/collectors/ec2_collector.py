import os
from datetime import datetime, timedelta
from typing import Iterable, Optional

from ..connectors.aws_connector_client import get_cloudwatch_metric_statistics
from ..models.metric_schema import Metric

DEFAULT_REGION = os.getenv("DEFAULT_METRICS_REGION")
DEFAULT_PERIOD = int(os.getenv("METRIC_PERIOD_SECONDS", "60"))
DEFAULT_WINDOW_MINUTES = int(os.getenv("METRIC_WINDOW_MINUTES", "60"))
# CloudWatch GetMetricStatistics permits at most 1,440 points. A 14-day
# evidence window therefore needs a 15-minute period (1,344 points).
HISTORICAL_PERIOD_SECONDS = 900


def _fetch_cw_stat(
    tenant_id: str,
    region: str,
    namespace: str,
    metric_name: str,
    dimension_name: str,
    dimension_val: str,
    stat: str,
    start_time: datetime,
    end_time: datetime,
    account_id: str | None = None,
) -> Optional[float]:
    payload = {
        "namespace": namespace,
        "metric_name": metric_name,
        "dimensions": [{"Name": dimension_name, "Value": dimension_val}],
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


def collect_ec2_metrics(
    tenant_id: str, instance_ids: Iterable, region: str = None
) -> list[Metric]:
    metrics = []
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=DEFAULT_WINDOW_MINUTES)
    iso_now = end_time.isoformat()

    for resource in instance_ids:
        instance_id, account_id, resource_region = _resource_parts(resource)
        metric_region = region or resource_region or DEFAULT_REGION
        if not instance_id or not account_id or not metric_region:
            continue
        # 1. CPU Utilization
        cpu_val = _fetch_cw_stat(
            tenant_id, metric_region, "AWS/EC2", "CPUUtilization", "InstanceId", instance_id, "Average", start_time, end_time, account_id
        )
        if cpu_val is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=instance_id,
                    metric_name="cpu_utilization",
                    timestamp=iso_now,
                    value=round(cpu_val, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="ec2",
                    labels={"resource_type": "ec2", "stat": "Average"},
                )
            )

        # 2. Network Bytes Total (NetworkIn + NetworkOut)
        net_in = _fetch_cw_stat(
            tenant_id, metric_region, "AWS/EC2", "NetworkIn", "InstanceId", instance_id, "Sum", start_time, end_time, account_id
        ) or 0.0
        net_out = _fetch_cw_stat(
            tenant_id, metric_region, "AWS/EC2", "NetworkOut", "InstanceId", instance_id, "Sum", start_time, end_time, account_id
        ) or 0.0
        net_total = net_in + net_out
        if net_total > 0:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=instance_id,
                    metric_name="network_bytes_total",
                    timestamp=iso_now,
                    value=round(net_total, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="ec2",
                    labels={"resource_type": "ec2", "stat": "Sum"},
                )
            )

        # 3. Disk Utilization (EBSReadBytes + EBSWriteBytes or DiskReadBytes + DiskWriteBytes)
        disk_read = _fetch_cw_stat(
            tenant_id, metric_region, "AWS/EC2", "EBSReadBytes", "InstanceId", instance_id, "Sum", start_time, end_time, account_id
        ) or 0.0
        disk_write = _fetch_cw_stat(
            tenant_id, metric_region, "AWS/EC2", "EBSWriteBytes", "InstanceId", instance_id, "Sum", start_time, end_time, account_id
        ) or 0.0
        if disk_read == 0 and disk_write == 0:
            disk_read = _fetch_cw_stat(
                tenant_id, metric_region, "AWS/EC2", "DiskReadBytes", "InstanceId", instance_id, "Sum", start_time, end_time, account_id
            ) or 0.0
            disk_write = _fetch_cw_stat(
                tenant_id, metric_region, "AWS/EC2", "DiskWriteBytes", "InstanceId", instance_id, "Sum", start_time, end_time, account_id
            ) or 0.0
        disk_total = disk_read + disk_write
        if disk_total > 0:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=instance_id,
                    metric_name="disk_utilization",
                    timestamp=iso_now,
                    value=round(disk_total, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="ec2",
                    labels={"resource_type": "ec2", "stat": "Sum"},
                )
            )

        # 4. Memory Utilization (CloudWatch agent only)
        mem_val = _fetch_cw_stat(
            tenant_id, metric_region, "CWAgent", "MemoryUtilization", "InstanceId", instance_id, "Average", start_time, end_time, account_id
        )
        if mem_val is None:
            mem_val = _fetch_cw_stat(
                tenant_id, metric_region, "CWAgent", "mem_used_percent", "InstanceId", instance_id, "Average", start_time, end_time, account_id
            )
        if mem_val is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=instance_id,
                    metric_name="memory_utilization",
                    timestamp=iso_now,
                    value=round(mem_val, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="ec2",
                    labels={"resource_type": "ec2", "stat": "Average"},
                )
            )

    return metrics
