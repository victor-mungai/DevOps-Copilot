"""Cost Optimization: Idle or Oversized RDS Instances."""
from ..base import AnalysisContext, make_finding


class IdleRdsRule:
    id = "cost.idle_rds"
    category = "cost_optimization"
    name = "Idle / Oversized RDS Database"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for rds_inst in ctx.rds:
            connections = rds_inst.get("connections")
            cpu = rds_inst.get("avg_cpu")
            db_id = rds_inst.get("db_id") or rds_inst.get("DBInstanceIdentifier") or rds_inst.get("resource_id")
            inst_class = rds_inst.get("instance_class") or rds_inst.get("DBInstanceClass")
            if not db_id or (connections is None and cpu is None):
                continue

            if connections == 0 or (cpu is not None and cpu < 5.0):
                account_id = rds_inst.get("account_id")
                region = rds_inst.get("region")
                observed_cost = ctx.resource_costs.get((account_id, db_id, region))
                inactive_hours = rds_inst.get("inactive_hours")
                monthly_stop_saving = (
                    (observed_cost / 14.0) * (inactive_hours / 24.0) * (30.0 / 14.0)
                    if observed_cost is not None and observed_cost > 0 and inactive_hours is not None else 0.0
                )
                cost_evidence = (
                    f"AWS Cost Explorer resource-attributed net spend was ${observed_cost:.8f} over the analysis window."
                    if observed_cost is not None else
                    "AWS Cost Explorer returned no resource-level cost for this database in the analysis window."
                )
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=db_id,
                        resource_type="rds",
                        severity="high",
                        category=self.category,
                        issue="Idle or Oversized RDS Database Instance",
                        recommendation="Metrics indicate an idle or underutilized database. Review its inactive windows and schedule stop/start for non-production periods; otherwise compare the next smaller AWS-supported DB instance class before resizing.",
                        confidence="high",
                        estimated_monthly_waste=round(monthly_stop_saving, 8),
                        avg_cpu=cpu,
                        instance_type=inst_class,
                        window_days=14.0,
                        aws_account_id=account_id,
                        region=region,
                        evidence=f"Connections={connections if connections is not None else 'No data available'}, average CPU={cpu if cpu is not None else 'No data available'}, inactive hours={inactive_hours if inactive_hours is not None else 'No data available'}. {cost_evidence} Projected monthly stop savings: ${monthly_stop_saving:.8f} based on observed resource spend and inactive hours. Rightsizing savings: No data available until AWS pricing confirms the target class.",
                        observed_cost=observed_cost,
                        inactive_hours=inactive_hours,
                    )
                )
        return findings


RULE = IdleRdsRule()
