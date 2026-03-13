import os
from typing import Iterable

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from ..models.metric_schema import Metric


def push_metrics(metrics: Iterable[Metric]) -> None:
    pushgateway_url = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
    if not pushgateway_url:
        return

    registry = CollectorRegistry()
    for metric in metrics:
        gauge = Gauge(
            metric.metric_name,
            "Resource metric",
            ["tenant", "resource"],
            registry=registry,
        )
        gauge.labels(metric.tenant_id, metric.resource_id).set(metric.value)

    push_to_gateway(pushgateway_url, job="metrics-collector", registry=registry)
