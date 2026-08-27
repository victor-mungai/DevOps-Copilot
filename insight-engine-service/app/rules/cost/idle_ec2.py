"""Cost: idle / underutilized EC2 (the original Feature 1 rule, now a rule pack)."""
import os

from ... import config
from ..base import AnalysisContext, make_finding

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
            inactivity_action = (
                "Metrics show sustained inactivity; schedule this instance to stop during the observed inactive window after validating workload requirements."
                if clearly_idle else
                "Review the observed inactive windows and schedule a stop policy only if the workload permits it."
            )
            cost_evidence = (
                f"AWS Cost Explorer resource-attributed net spend was ${s.observed_cost:.2f} over the last {s.cost_window_days} days."
                if s.observed_cost is not None
                else "No resource-level cost data available from AWS Cost Explorer for this instance."
            )
            inactive_hours = s.inactive_hours
            monthly_stop_saving = (
                (s.observed_cost / s.cost_window_days) * (inactive_hours / 24.0) * (30.0 / s.cost_window_days)
                if s.observed_cost is not None and s.observed_cost > 0 and inactive_hours is not None and s.cost_window_days
                else 0.0
            )
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=s.resource_id,
                    resource_type="ec2",
                    severity="medium",
                    category=self.category,
                    issue="Underutilized EC2 Instance",
                    recommendation=f"{inactivity_action} For active periods, evaluate the next smaller size in the same AWS instance family ({s.instance_type or 'current type'}). Compare the candidate price in AWS before applying it.",
                    confidence="high" if clearly_idle else "medium",
                    estimated_monthly_waste=round(monthly_stop_saving, 8),
                    avg_cpu=round(s.avg_cpu, 2),
                    instance_type=s.instance_type,
                    window_days=float(config.IDLE_WINDOW_DAYS),
                    aws_account_id=s.account_id,
                    region=s.region,
                    evidence=(
                        f"CloudWatch CPU averaged {s.avg_cpu:.2f}% across {s.samples} samples over "
                        f"{config.IDLE_WINDOW_DAYS} days. Inactive hours observed: {inactive_hours if inactive_hours is not None else 'No data available'}. {cost_evidence} "
                        f"Projected monthly stop savings: ${monthly_stop_saving:.8f} based on observed resource spend and inactive hours."
                    ),
                    observed_cost=s.observed_cost,
                    inactive_hours=inactive_hours,
                )
            )
        return findings


RULE = IdleEc2Rule()
