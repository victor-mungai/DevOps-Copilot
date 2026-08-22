import logging
import os
from typing import Optional

import requests

from .. import config

logger = logging.getLogger("insight-engine")


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

    def avg_cpu_over_window(
        self, tenant_id: str, resource_id: str, days: int
    ) -> Optional[dict]:
        assert tenant_id, "tenant_id is required"
        selector = (
            f'{config.METRIC_NAME_CPU}'
            f'{{{config.LABEL_TENANT}="{tenant_id}",'
            f'{config.LABEL_RESOURCE}="{resource_id}"}}'
        )
        window = f"[{days}d]"

        avg = self._instant_query(f"avg_over_time({selector}{window})")
        if avg is None:
            return None
        samples = self._instant_query(f"count_over_time({selector}{window})") or 0.0
        return {"avg": avg, "samples": int(samples)}
