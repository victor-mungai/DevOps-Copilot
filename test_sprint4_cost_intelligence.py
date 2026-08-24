#!/usr/bin/env python3
"""Automated Verification Suite — Sprint 4: Cost Intelligence & FinOps Visibility."""

import json
import os
import sys
import unittest
import urllib.request

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

TENANT_A = "1a81c82d-d090-4dbd-96db-27c09f982bbc"
TENANT_B = "b04422b6-a588-4e39-8343-eb15e1334134"


class TestSprint4CostIntelligence(unittest.TestCase):

    def _http_get(self, url: str, tenant_id: str) -> dict | list:
        req = urllib.request.Request(url, headers={"X-Tenant-ID": tenant_id})
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode("utf-8"))

    def _http_post(self, url: str, tenant_id: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "X-Tenant-ID": tenant_id},
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode("utf-8"))

    def test_01_cost_collector_health(self):
        """Verify cost-collector-service /health port 8006."""
        with urllib.request.urlopen("http://127.0.0.1:8006/health", timeout=3) as res:
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("service"), "cost-collector-service")

    def test_02_gateway_cost_summary(self):
        """Verify Gateway /v1/cost/summary returns Executive spend cards."""
        data = self._http_get("http://127.0.0.1:8000/v1/cost/summary?range=30d", TENANT_A)
        self.assertIn("total", data)
        self.assertIn("projected_monthly", data)
        self.assertIn("potential_savings", data)
        self.assertIn("optimization_score", data)
        self.assertGreater(data["total"], 0)

    def test_03_gateway_cost_trend(self):
        """Verify Gateway /v1/cost/trend returns 30-day interactive curve."""
        data = self._http_get("http://127.0.0.1:8000/v1/cost/trend?range=30d", TENANT_A)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("cost", data[0])
        self.assertIn("previous_cost", data[0])

    def test_04_gateway_cost_breakdowns(self):
        """Verify Gateway service, region, and account cost breakdowns."""
        services = self._http_get("http://127.0.0.1:8000/v1/cost/services?range=30d", TENANT_A)
        self.assertIsInstance(services, list)
        self.assertGreater(len(services), 0)

        regions = self._http_get("http://127.0.0.1:8000/v1/cost/regions?range=30d", TENANT_A)
        self.assertIsInstance(regions, list)
        self.assertGreater(len(regions), 0)

        accounts = self._http_get("http://127.0.0.1:8000/v1/cost/accounts?range=30d", TENANT_A)
        self.assertIsInstance(accounts, list)
        self.assertGreater(len(accounts), 0)

    def test_05_async_rabbitmq_cost_collection(self):
        """Verify POST /v1/cost/collect emits cost.collection.requested event."""
        data = self._http_post("http://127.0.0.1:8000/v1/cost/collect?region=us-east-2", TENANT_A)
        self.assertEqual(data.get("status"), "queued")
        self.assertEqual(data.get("tenant_id"), TENANT_A)
        self.assertIn("event", data)

    def test_06_ai_cost_copilot_explanation(self):
        """Verify AI Copilot grounds financial answers in billing & optimization context."""
        payload = {"question": "Why did our AWS spend increase this month?"}
        data = self._http_post(
            f"http://127.0.0.1:8000/v1/insights/{TENANT_A}/explain", TENANT_A, payload
        )
        self.assertIn("answer", data)
        self.assertIn("Spend", data["answer"])
        self.assertIn("Savings", data["answer"])

    def test_07_tenant_isolation_enforcement(self):
        """Verify strict tenant isolation for cost data."""
        data_a = self._http_get("http://127.0.0.1:8000/v1/cost/summary?range=30d", TENANT_A)
        data_b = self._http_get("http://127.0.0.1:8000/v1/cost/summary?range=30d", TENANT_B)
        self.assertEqual(data_a["tenant_id"], TENANT_A)
        self.assertEqual(data_b["tenant_id"], TENANT_B)


if __name__ == "__main__":
    unittest.main(verbosity=2)
