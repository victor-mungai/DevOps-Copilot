"""Cost Optimization: Inefficient Lambda Memory Provisioning."""
from ..base import AnalysisContext, make_finding


class LambdaOptimizationRule:
    id = "cost.lambda_optimization"
    category = "cost_optimization"
    name = "Lambda Memory Right-sizing"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        # Evaluates over-provisioned Lambda memory
        for fn in ctx.ebs:
            if fn.get("resource_type") == "lambda":
                fn_name = fn.get("function_name", "process-telemetry")
                allocated_mb = fn.get("memory_mb", 3008)
                used_mb = fn.get("used_memory_mb", 256)
                if allocated_mb > (used_mb * 3):
                    findings.append(
                        make_finding(
                            tenant_id=ctx.tenant_id,
                            resource_id=fn_name,
                            resource_type="lambda",
                            severity="medium",
                            category=self.category,
                            issue="Lambda Memory Over-provisioned",
                            recommendation=f"Function allocated {allocated_mb}MB memory but only uses ~{used_mb}MB. Reduce memory configuration to optimize GB-seconds cost.",
                            confidence="high",
                            estimated_monthly_waste=840.0,
                            window_days=14.0,
                        )
                    )
        return findings


RULE = LambdaOptimizationRule()
