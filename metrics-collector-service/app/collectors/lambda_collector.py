import os
from datetime import datetime, timedelta
from typing import Iterable, Optional

from ..connectors.aws_connector_client import get_cloudwatch_metric_statistics
from ..models.metric_schema import Metric

DEFAULT_REGION = os.getenv("DEFAULT_METRICS_REGION")
HISTORICAL_PERIOD_SECONDS = 900


def _fetch_lambda_stat(
    tenant_id: str,
    region: str,
    metric_name: str,
    function_name: str,
    stat: str,
    end_time: datetime,
    account_id: str | None = None,
) -> Optional[float]:
    payload = {
        "namespace": "AWS/Lambda",
        "metric_name": metric_name,
        "dimensions": [{"Name": "FunctionName", "Value": function_name}],
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


def collect_lambda_metrics(
    tenant_id: str, function_names: Iterable, region: str = None
) -> list[Metric]:
    metrics = []
    end_time = datetime.utcnow()
    iso_now = end_time.isoformat()

    for resource in function_names:
        function_name, account_id, resource_region = _resource_parts(resource)
        metric_region = region or resource_region or DEFAULT_REGION
        if not function_name or not account_id or not metric_region:
            continue
        invocations = _fetch_lambda_stat(tenant_id, metric_region, "Invocations", function_name, "Sum", end_time, account_id)
        if invocations is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=function_name,
                    metric_name="invocations",
                    timestamp=iso_now,
                    value=round(invocations, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="lambda",
                    labels={"resource_type": "lambda", "stat": "Sum"},
                )
            )

        duration = _fetch_lambda_stat(tenant_id, metric_region, "Duration", function_name, "Average", end_time, account_id)
        if duration is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=function_name,
                    metric_name="duration_ms",
                    timestamp=iso_now,
                    value=round(duration, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="lambda",
                    labels={"resource_type": "lambda", "stat": "Average"},
                )
            )

        errors = _fetch_lambda_stat(tenant_id, metric_region, "Errors", function_name, "Sum", end_time, account_id)
        if errors is not None:
            metrics.append(
                Metric(
                    tenant_id=tenant_id,
                    resource_id=function_name,
                    metric_name="errors",
                    timestamp=iso_now,
                    value=round(errors, 2),
                    aws_account_id=account_id,
                    region=metric_region,
                    resource_type="lambda",
                    labels={"resource_type": "lambda", "stat": "Sum"},
                )
            )

    return metrics
