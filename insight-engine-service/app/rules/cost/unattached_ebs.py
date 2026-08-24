"""Cost Optimization: Unattached EBS Storage Volumes."""
from ..base import AnalysisContext, make_finding


class UnattachedEbsRule:
    id = "cost.unattached_ebs"
    category = "cost_optimization"
    name = "Unattached EBS Volume Cleanup"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for vol in ctx.ebs:
            state = vol.get("state", "").lower()
            vol_id = vol.get("volume_id", "vol-0123456789abcdef0")
            size_gb = float(vol.get("size", 100))

            if state in ("available", "unattached"):
                monthly_waste = round(size_gb * 0.10, 2)
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=vol_id,
                        resource_type="ebs",
                        severity="medium",
                        category=self.category,
                        issue="Unattached EBS Volume",
                        recommendation="EBS volume is not attached to any EC2 instance. Delete volume or archive snapshot.",
                        confidence="high",
                        estimated_monthly_waste=monthly_waste,
                        window_days=14.0,
                    )
                )
        return findings


RULE = UnattachedEbsRule()
