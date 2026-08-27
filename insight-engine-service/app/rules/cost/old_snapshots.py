"""Cost Optimization: Old EBS Snapshots (> 30 days)."""
from ..base import AnalysisContext, make_finding


class OldSnapshotsRule:
    id = "cost.old_snapshots"
    category = "cost_optimization"
    name = "Aged EBS Snapshots Cleanup"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        # Checks snapshots older than 30 days
        for snap in ctx.ebs:
            if snap.get("is_snapshot") and snap.get("age_days", 0) > 30:
                snap_id = snap.get("snapshot_id")
                if not snap_id:
                    continue
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=snap_id,
                        resource_type="ebs_snapshot",
                        severity="low",
                        category=self.category,
                        issue="Stale EBS Snapshot (>30 days old)",
                        recommendation="Review and delete outdated EBS snapshots to reduce monthly storage costs.",
                        confidence="high",
                        estimated_monthly_waste=0.0,
                        window_days=30.0,
                    )
                )
        return findings


RULE = OldSnapshotsRule()
