"""Cost: oversized EC2 — a large instance type running at consistently modest
CPU (not idle enough for the idle rule, but a clear downsize candidate)."""
import os

from ..base import AnalysisContext, make_finding

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
            family = s.instance_type.rsplit(".", 1)[0] if s.instance_type else None
            current_size = s.instance_type.rsplit(".", 1)[-1] if s.instance_type else None
            cost_evidence = (
                f"AWS Cost Explorer resource-attributed net spend was ${s.observed_cost:.2f} over the last {s.cost_window_days} days."
                if s.observed_cost is not None
                else "No resource-level cost data available from AWS Cost Explorer for this instance."
            )
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=s.resource_id,
                    resource_type="ec2",
                    severity="low",
                    category=self.category,
                    issue="Oversized EC2 Instance",
                    recommendation=f"CPU stays well below capacity; compare the next smaller size in the same AWS family ({family + '.' if family else ''}{current_size or 'current type'}) using AWS pricing, then validate workload demand before changing it.",
                    confidence="medium",
                    estimated_monthly_waste=0.0,
                    avg_cpu=round(s.avg_cpu, 2),
                    instance_type=s.instance_type,
                    aws_account_id=s.account_id,
                    region=s.region,
                    evidence=(
                        f"CloudWatch CPU averaged {s.avg_cpu:.2f}% across {s.samples} samples. {cost_evidence} Rightsizing savings: No data available until AWS pricing confirms the smaller type."
                    ),
                    observed_cost=s.observed_cost,
                )
            )
        return findings


RULE = OversizedEc2Rule()
