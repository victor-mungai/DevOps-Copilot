"""Cost: idle EBS volumes (available/unattached).

Structured and ready; produces findings once the connector exposes EBS volumes
(ctx.ebs). Until then it evaluates the empty list and returns nothing.
"""
from ..base import AnalysisContext, make_finding

# Rough monthly $/GB for gp3, used when volume size is known.
GP3_USD_PER_GB_MONTH = 0.08


class IdleEbsRule:
    id = "cost.idle_ebs"
    category = "cost_optimization"
    name = "Idle EBS Volumes"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for vol in ctx.ebs:
            if vol.get("state") != "available":  # unattached
                continue
            size_gb = float(vol.get("size_gb", 0) or 0)
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=vol.get("volume_id", "unknown"),
                    resource_type="ebs",
                    severity="low",
                    category=self.category,
                    issue="Unattached EBS Volume",
                    recommendation="Snapshot if needed, then delete this unattached volume.",
                    confidence="high",
                    estimated_monthly_waste=round(size_gb * GP3_USD_PER_GB_MONTH, 2),
                )
            )
        return findings


RULE = IdleEbsRule()
