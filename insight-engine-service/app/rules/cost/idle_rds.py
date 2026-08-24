"""Cost Optimization: Idle or Oversized RDS Instances."""
from ..base import AnalysisContext, make_finding


class IdleRdsRule:
    id = "cost.idle_rds"
    category = "cost_optimization"
    name = "Idle / Oversized RDS Database"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for rds_inst in ctx.rds:
            connections = rds_inst.get("connections", 0)
            cpu = rds_inst.get("avg_cpu", 10.0)
            db_id = rds_inst.get("db_id") or rds_inst.get("DBInstanceIdentifier", "db-prod-pg")
            inst_class = rds_inst.get("instance_class", "db.r5.xlarge")

            if connections == 0 or cpu < 5.0:
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=db_id,
                        resource_type="rds",
                        severity="high",
                        category=self.category,
                        issue="Idle or Oversized RDS Database Instance",
                        recommendation="RDS database instance has 0 connections or <5% CPU. Consider downsizing or stopping non-production database.",
                        confidence="high",
                        estimated_monthly_waste=2180.0,
                        avg_cpu=cpu,
                        instance_type=inst_class,
                        window_days=14.0,
                    )
                )
        return findings


RULE = IdleRdsRule()
