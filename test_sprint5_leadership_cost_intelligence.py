#!/usr/bin/env python3
"""Automated Verification Suite — Sprint 5: Leadership Cost Intelligence & Data Accuracy."""

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


class TestSprint5LeadershipCostIntelligence(unittest.TestCase):

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

    def test_01_cost_reconciliation_zero_variance(self):
        """Verify GET /v1/cost/reconciliation returns status RECONCILED with 0.0 variance."""
        data = self._http_get("http://127.0.0.1:8000/v1/cost/reconciliation", TENANT_A)
        self.assertEqual(data.get("status"), "RECONCILED")
        self.assertEqual(data.get("variance"), 0.0)
        self.assertEqual(data.get("cost_basis"), "AMORTIZED")
        self.assertEqual(data.get("currency"), "USD")

    def test_02_cost_summary_calculation_basis(self):
        """Verify GET /v1/cost/summary exposes calculation basis & MTD comparisons."""
        data = self._http_get("http://127.0.0.1:8000/v1/cost/summary?range=30d", TENANT_A)
        self.assertEqual(data.get("cost_basis"), "AMORTIZED")
        self.assertEqual(data.get("currency"), "USD")
        self.assertIn("mtd_spend", data)
        self.assertIn("previous_equivalent_period_spend", data)
        self.assertIn("previous_full_month_spend", data)
        self.assertIn("projected_monthly", data)
        self.assertIn("budget", data)
        self.assertIn("projected_variance", data)

    def test_03_analysis_coverage_100_percent(self):
        """Verify GET /v1/insights/coverage returns 100% analysis coverage of all resources."""
        data = self._http_get("http://127.0.0.1:8000/v1/insights/coverage", TENANT_A)
        self.assertEqual(data.get("coverage_percent"), 100)
        self.assertGreater(data.get("total_resources"), 0)
        self.assertEqual(data.get("total_resources"), data.get("resources_analyzed"))
        self.assertIn("health_summary", data)

    def test_04_canonical_resource_naming(self):
        """Verify resources have human-readable display names with technical IDs."""
        data = self._http_get("http://127.0.0.1:8000/v1/insights/coverage", TENANT_A)
        resources = data.get("resources", [])
        self.assertGreater(len(resources), 0)
        for res in resources:
            self.assertIn("display_name", res)
            self.assertIn("resource_id", res)
            self.assertIn("resource_type", res)
            self.assertIn("health_state", res)

    def test_05_cost_copilot_explanation(self):
        """Verify AI Copilot provides structured cost savings answers."""
        payload = {"question": "Where can we save money?"}
        data = self._http_post(
            f"http://127.0.0.1:8000/v1/insights/{TENANT_A}/explain", TENANT_A, payload
        )
        self.assertIn("answer", data)
        self.assertIn("Savings", data["answer"])

    def test_06_tenant_isolation_enforcement(self):
        """Verify strict multi-tenant isolation across Tenant A and Tenant B."""
        data_a = self._http_get("http://127.0.0.1:8000/v1/cost/reconciliation", TENANT_A)
        data_b = self._http_get("http://127.0.0.1:8000/v1/cost/reconciliation", TENANT_B)
        self.assertEqual(data_a["tenant_id"], TENANT_A)
        self.assertEqual(data_b["tenant_id"], TENANT_B)


if __name__ == "__main__":
    unittest.main(verbosity=2)
