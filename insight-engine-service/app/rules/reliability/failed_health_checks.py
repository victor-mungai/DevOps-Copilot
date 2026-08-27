"""Reliability: failed health checks. Ready; needs ELB/target-group health from
the connector (ctx has no health data yet), so it currently finds nothing."""
from ..base import AnalysisContext


class FailedHealthChecksRule:
    id = "reliability.failed_health_checks"
    category = "reliability"
    name = "Failed Health Checks"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        return []


RULE = FailedHealthChecksRule()
