import abc
import logging
import os
from typing import Iterable

import httpx
from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway

from ..models.metric_schema import Metric

logger = logging.getLogger("metrics-collector.storage")


class MetricsStorage(abc.ABC):
    @abc.abstractmethod
    def push(self, metrics: Iterable[Metric]) -> None:
        raise NotImplementedError


class PushgatewayStorage(MetricsStorage):
    """Local Development Metrics Storage (Pushgateway -> Prometheus)."""

    def __init__(self, pushgateway_url: str | None = None):
        self.pushgateway_url = pushgateway_url or os.getenv("PROMETHEUS_PUSHGATEWAY_URL", "http://127.0.0.1:9091")

    def push(self, metrics: Iterable[Metric]) -> None:
        if not self.pushgateway_url:
            return

        gateway = self.pushgateway_url.replace("http://", "").replace("https://", "").rstrip("/")
        by_resource: dict[str, list[Metric]] = {}
        for metric in metrics:
            by_resource.setdefault(metric.resource_id, []).append(metric)

        for resource_id, resource_metrics in by_resource.items():
            registry = CollectorRegistry()
            gauges = {}
            for metric in resource_metrics:
                if metric.metric_name not in gauges:
                    try:
                        gauges[metric.metric_name] = Gauge(
                            metric.metric_name,
                            "Resource metric",
                            ["tenant", "resource", "aws_account_id", "region", "resource_type"],
                            registry=registry,
                        )
                    except ValueError:
                        pass
                if metric.metric_name in gauges:
                    try:
                        gauges[metric.metric_name].labels(
                            metric.tenant_id,
                            metric.resource_id,
                            metric.aws_account_id,
                            metric.region,
                            metric.resource_type,
                        ).set(metric.value)
                    except Exception:
                        pass

            try:
                pushadd_to_gateway(
                    gateway,
                    job="metrics-collector",
                    grouping_key={"instance": resource_id},
                    registry=registry,
                )
            except Exception as e:
                logger.error(f"Pushgateway push failed for resource {resource_id}: {e}")


class AMPStorage(MetricsStorage):
    """Production Amazon Managed Service for Prometheus Remote Write Storage."""

    def __init__(self, amp_endpoint: str | None = None):
        self.amp_endpoint = amp_endpoint or os.getenv("AMP_REMOTE_WRITE_URL", "")

    def push(self, metrics: Iterable[Metric]) -> None:
        if not self.amp_endpoint:
            logger.warning("AMP_REMOTE_WRITE_URL not configured. Skipping AMP push.")
            return

        payload = {
            "metrics": [
                {
                    "metric": m.metric_name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "labels": {
                        "tenant": m.tenant_id,
                        "resource": m.resource_id,
                        "aws_account_id": m.aws_account_id,
                        "region": m.region,
                        "resource_type": m.resource_type,
                        **m.labels,
                    },
                }
                for m in metrics
            ]
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.amp_endpoint, json=payload)
                resp.raise_for_status()
        except Exception as exc:
            logger.error(f"AMP Remote Write push error: {exc}")


def get_metrics_storage() -> MetricsStorage:
    backend = os.getenv("METRICS_STORAGE_BACKEND", "pushgateway").lower()
    if backend == "amp":
        return AMPStorage()
    return PushgatewayStorage()
