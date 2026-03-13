import os
from datetime import datetime, timedelta
from typing import Iterable

from ..connectors.aws_connector_client import get_cloudwatch_metric_statistics
from ..models.metric_schema import Metric

DEFAULT_REGION = os.getenv("DEFAULT_METRICS_REGION", "us-east-1")
DEFAULT_PERIOD = int(os.getenv("METRIC_PERIOD_SECONDS", "60"))
DEFAULT_WINDOW_MINUTES = int(os.getenv("METRIC_WINDOW_MINUTES", "5"))


def collect_rds_metrics(tenant_id: str, db_ids: Iterable[str]) -> list[Metric]:
    metrics = []
    for db_id in db_ids:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=DEFAULT_WINDOW_MINUTES)
        payload = {
            "namespace": "AWS/RDS",
            "metric_name": "CPUUtilization",
            "dimensions": [{"Name": "DBInstanceIdentifier", "Value": db_id}],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "period": DEFAULT_PERIOD,
            "statistics": ["Average"],
            "region": DEFAULT_REGION,
        }
        response = get_cloudwatch_metric_statistics(tenant_id, payload)
        datapoints = response.get("data", {}).get("Datapoints", [])
        for datapoint in sorted(
            datapoints, key=lambda x: x.get("Timestamp", ""), reverse=True
        )[:1]:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=db_id,
                    metric_name="cpu_utilization",
                    timestamp=datapoint["Timestamp"],
                    value=float(datapoint.get("Average", 0.0)),
                    labels={"resource_type": "rds", "stat": "Average"},
                )
            )
    return metrics
