"""Cost: idle / underutilized EC2 (the original Feature 1 rule, now a rule pack)."""
import os

from ... import config
from ..base import AnalysisContext, make_finding
from ..cost_table import estimate_monthly_cost

MIN_SAMPLES_FOR_VERDICT = int(os.getenv("IDLE_MIN_SAMPLES", "60"))


class IdleEc2Rule:
    id = "cost.idle_ec2"
    category = "cost_optimization"
    name = "Idle / Underutilized EC2"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for s in ctx.ec2:
            if s.avg_cpu is None or s.samples < MIN_SAMPLES_FOR_VERDICT:
                continue
            if s.avg_cpu >= config.IDLE_CPU_THRESHOLD:
                continue
            clearly_idle = s.avg_cpu < (config.IDLE_CPU_THRESHOLD / 2)
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=s.resource_id,
                    resource_type="ec2",
                    severity="medium",
                    category=self.category,
                    issue="Underutilized EC2 Instance",
                    recommendation="Consider downsizing or terminating this instance.",
                    confidence="high" if clearly_idle else "medium",
                    estimated_monthly_waste=estimate_monthly_cost(s.instance_type),
                    avg_cpu=round(s.avg_cpu, 2),
                    instance_type=s.instance_type,
                    window_days=float(config.IDLE_WINDOW_DAYS),
                )
            )
        return findings


RULE = IdleEc2Rule()
