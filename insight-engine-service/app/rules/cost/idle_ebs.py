"""Cost: idle EBS volumes (available/unattached).

Structured and ready; produces findings once the connector exposes EBS volumes
(ctx.ebs). Until then it evaluates the empty list and returns nothing.
"""
from ..base import AnalysisContext, make_finding


class IdleEbsRule:
    id = "cost.idle_ebs"
    category = "cost_optimization"
    name = "Idle EBS Volumes"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for vol in ctx.ebs:
            if vol.get("state") != "available":  # unattached
                continue
            volume_id = vol.get("volume_id")
            if not volume_id:
                continue
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=volume_id,
                    resource_type="ebs",
                    severity="low",
                    category=self.category,
                    issue="Unattached EBS Volume",
                    recommendation="Snapshot if needed, then delete this unattached volume.",
                    confidence="high",
                    estimated_monthly_waste=0.0,
                )
            )
        return findings


RULE = IdleEbsRule()
