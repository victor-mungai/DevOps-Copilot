import logging
import os
import re
from typing import Optional

import requests

from .. import config

logger = logging.getLogger("insight-engine")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9._\-:/ ]+$")


def _safe_label(value: str, field: str) -> str:
    if not value or not _SAFE_LABEL.match(value):
        raise ValueError(f"invalid {field}")
    return value


class PrometheusMetricSource:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("PROMETHEUS_URL", getattr(config, "PROMETHEUS_URL", "http://18.116.65.134:9090"))).rstrip("/")

    def _instant_query(self, promql: str) -> Optional[float]:
        url = f"{self.base_url}/api/v1/query"
        try:
            resp = requests.get(
                url, params={"query": promql}, timeout=config.HTTP_TIMEOUT
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Prometheus query failed: %s (%s)", exc, promql)
            return None

        body = resp.json()
        if body.get("status") != "success":
            logger.warning("Prometheus query non-success: %s", body.get("error"))
            return None

        result = body.get("data", {}).get("result", [])
        if not result:
            return None
        try:
            return float(result[0]["value"][1])
        except (KeyError, IndexError, ValueError, TypeError):
            return None

    def _selector(self, tenant_id: str, resource_id: str, metric_name: str) -> str:
        return (
            f'{_safe_label(metric_name, "metric_name")}'
            f'{{{config.LABEL_TENANT}="{_safe_label(tenant_id, "tenant_id")}",'
            f'{config.LABEL_RESOURCE}="{_safe_label(resource_id, "resource_id")}"}}'
        )

    def avg_cpu_over_window(
        self, tenant_id: str, resource_id: str, days: int
    ) -> Optional[dict]:
        assert tenant_id, "tenant_id is required"
        tenant_id = _safe_label(tenant_id, "tenant_id")
        resource_id = _safe_label(resource_id, "resource_id")
        selector = self._selector(tenant_id, resource_id, config.METRIC_NAME_CPU)
        window = f"[{days}d]"

        avg = self._instant_query(f"avg_over_time({selector}{window})")
        if avg is None:
            return None
        samples = self._instant_query(f"count_over_time({selector}{window})") or 0.0
        return {"avg": avg, "samples": int(samples)}

    def inactive_hours_over_window(self, tenant_id: str, resource_id: str, days: int, threshold: float) -> Optional[float]:
        """Count hours where Prometheus observed CPU below the configured threshold."""
        selector = self._selector(tenant_id, resource_id, config.METRIC_NAME_CPU)
        query = f'count_over_time(({selector} < {threshold})[{days}d:5m]) * 5 / 60'
        return self._instant_query(query)

    def aggregate_over_window(
        self, tenant_id: str, resource_id: str, metric_name: str, days: int, aggregation: str = "avg"
    ) -> Optional[dict]:
        """Read an observed metric aggregate without supplying synthetic defaults."""
        selector = self._selector(tenant_id, resource_id, metric_name)
        fn = "sum_over_time" if aggregation == "sum" else "avg_over_time"
        value = self._instant_query(f"{fn}({selector}[{days}d])")
        if value is None:
            return None
        samples = self._instant_query(f"count_over_time({selector}[{days}d])") or 0.0
        return {"value": value, "samples": int(samples)}
