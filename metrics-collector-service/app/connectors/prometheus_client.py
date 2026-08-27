import os
from typing import Iterable

from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway

from ..models.metric_schema import Metric


from .storage import get_metrics_storage


def push_metrics(metrics: Iterable[Metric]) -> None:
    storage = get_metrics_storage()
    storage.push(metrics)
