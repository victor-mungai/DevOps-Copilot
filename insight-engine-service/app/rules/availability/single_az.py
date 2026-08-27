"""Availability: workloads concentrated in a single AZ. Ready; needs per-AZ
placement across instances (connector exposes AZ per instance, but multi-instance
topology analysis is future work), so it currently finds nothing."""
from ..base import AnalysisContext


class SingleAzRule:
    id = "availability.single_az"
    category = "availability"
    name = "Single-AZ Concentration"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        return []


RULE = SingleAzRule()
