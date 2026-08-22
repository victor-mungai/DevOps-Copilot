"""Performance: high disk usage. Ready; activates once a disk metric is emitted."""
from ..base import AnalysisContext


class HighDiskRule:
    id = "performance.high_disk"
    category = "performance"
    name = "High Disk Usage"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        # Requires a per-instance disk metric that is not collected yet.
        return []


RULE = HighDiskRule()
