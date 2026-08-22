"""Cost: oversized EC2 — a large instance type running at consistently modest
CPU (not idle enough for the idle rule, but a clear downsize candidate)."""
import os

from ..base import AnalysisContext, make_finding
from ..cost_table import estimate_monthly_cost

# Types considered "large" for the purpose of downsizing suggestions.
LARGE_TYPES = {"xlarge", "2xlarge", "4xlarge", "metal", "large"}
OVERSIZED_CPU_CEILING = float(os.getenv("OVERSIZED_CPU_CEILING", "25.0"))
OVERSIZED_CPU_FLOOR = float(os.getenv("IDLE_CPU_THRESHOLD", "5.0"))
MIN_SAMPLES = int(os.getenv("IDLE_MIN_SAMPLES", "60"))


def _is_large(instance_type: str | None) -> bool:
    if not instance_type:
        return False
    size = instance_type.split(".")[-1]
    return size in LARGE_TYPES


class OversizedEc2Rule:
    id = "cost.oversized_ec2"
    category = "cost_optimization"
    name = "Oversized EC2"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for s in ctx.ec2:
            if s.avg_cpu is None or s.samples < MIN_SAMPLES:
                continue
            # Above the idle floor (so idle_ec2 won't also flag it) but well
            # under a healthy utilization band, on a large type.
            if not _is_large(s.instance_type):
                continue
            if not (OVERSIZED_CPU_FLOOR <= s.avg_cpu < OVERSIZED_CPU_CEILING):
                continue
            # Downsizing one step ≈ saves ~half the monthly cost (heuristic).
            waste = round(estimate_monthly_cost(s.instance_type) * 0.5, 2)
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=s.resource_id,
                    resource_type="ec2",
                    severity="low",
                    category=self.category,
                    issue="Oversized EC2 Instance",
                    recommendation="CPU stays well below capacity; downsize to a smaller instance type.",
                    confidence="medium",
                    estimated_monthly_waste=waste,
                    avg_cpu=round(s.avg_cpu, 2),
                    instance_type=s.instance_type,
                )
            )
        return findings


RULE = OversizedEc2Rule()
