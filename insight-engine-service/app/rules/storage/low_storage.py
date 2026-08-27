import os
from ..base import AnalysisContext, Rule, make_finding

MIN_FREE_STORAGE_GB = float(os.getenv("RULE_MIN_FREE_STORAGE_GB", "10.0"))


class LowStorageRule:
    id = "storage_low_space"
    category = "reliability"
    name = "Low Storage Availability"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings = []
        for rds in ctx.rds:
            if isinstance(rds, dict):
                db_id = rds.get("resource_id") or rds.get("DBInstanceIdentifier")
                free_gb = rds.get("free_storage_gb")
                if db_id and free_gb is not None and free_gb < MIN_FREE_STORAGE_GB:
                    findings.append(
                        make_finding(
                            tenant_id=ctx.tenant_id,
                            resource_id=db_id,
                            resource_type="rds",
                            severity="critical",
                            category=self.category,
                            issue=f"RDS instance {db_id} has low remaining storage space ({free_gb:.1f} GB remaining)",
                            recommendation="Enable storage auto-scaling or increase allocated storage capacity immediately.",
                            confidence="high",
                        )
                    )
        return findings


RULE: Rule = LowStorageRule()
