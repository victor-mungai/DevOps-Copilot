"""Reliability: repeated restarts. Ready; needs instance state-transition history
from the connector, which is not collected yet."""
from ..base import AnalysisContext


class RepeatedRestartsRule:
    id = "reliability.repeated_restarts"
    category = "reliability"
    name = "Repeated Restarts"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        return []


RULE = RepeatedRestartsRule()
