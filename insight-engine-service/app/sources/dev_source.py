"""Offline synthetic provider for local development (METRIC_SOURCE=dev).

Reads tenant -> instances (with a synthetic CPU average) from a seed JSON file,
so the insight loop runs without Prometheus or AWS. Build one with
scripts/seed_dev.py.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger("insight-engine")

DEFAULT_SEED_FILE = os.getenv("SEED_FILE", "./seed_metrics.json")


class DevSource:
    def __init__(self, seed_file: Optional[str] = None):
        self.seed_file = seed_file or DEFAULT_SEED_FILE

    def _load(self) -> dict:
        try:
            with open(self.seed_file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            logger.warning("Seed file not found: %s", self.seed_file)
            return {"tenants": {}}
        except json.JSONDecodeError as exc:
            logger.warning("Seed file invalid JSON: %s", exc)
            return {"tenants": {}}

    def _tenant_rows(self, tenant_id: str) -> list[dict]:
        return self._load().get("tenants", {}).get(tenant_id, [])

    def list_ec2_instances(self, tenant_id: str) -> list[dict]:
        assert tenant_id, "tenant_id is required"
        return [
            {"instance_id": r["instance_id"], "instance_type": r.get("instance_type")}
            for r in self._tenant_rows(tenant_id)
        ]

    def avg_cpu_over_window(self, tenant_id: str, resource_id: str, days: int):
        assert tenant_id, "tenant_id is required"
        for row in self._tenant_rows(tenant_id):
            if row["instance_id"] == resource_id:
                return {
                    "avg": float(row.get("avg_cpu", 0.0)),
                    "samples": int(row.get("samples", 0)),
                }
        return None
