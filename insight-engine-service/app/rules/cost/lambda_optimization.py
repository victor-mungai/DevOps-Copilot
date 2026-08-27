"""Cost Optimization: Inefficient Lambda Memory Provisioning."""
from ..base import AnalysisContext, make_finding


class LambdaOptimizationRule:
    id = "cost.lambda_optimization"
    category = "cost_optimization"
    name = "Lambda Memory Right-sizing"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        # Evaluates over-provisioned Lambda memory when AWS/metrics provide both
        # configured and observed memory usage. No synthetic defaults.
        for fn in ctx.lambda_functions:
            if fn.get("resource_type", "lambda") == "lambda":
                fn_name = fn.get("function_name") or fn.get("resource_id")
                allocated_mb = fn.get("memory_mb")
                used_mb = fn.get("used_memory_mb")
                invocations = fn.get("invocations")
                if not fn_name:
                    continue
                over_memory = allocated_mb is not None and used_mb is not None and allocated_mb > (used_mb * 3)
                inactive = invocations is not None and invocations == 0 and fn.get("metric_samples", 0) > 0
                if over_memory or inactive:
                    account_id = fn.get("account_id")
                    region = fn.get("region")
                    observed_cost = ctx.resource_costs.get((account_id, fn_name, region))
                    cost_evidence = (
                        f"AWS Cost Explorer resource-attributed net spend was ${observed_cost:.8f} over the analysis window."
                        if observed_cost is not None else
                        "AWS Cost Explorer returned no resource-level cost for this function in the analysis window."
                    )
                    monthly_stop_saving = (observed_cost / 14.0) * 30.0 if inactive and observed_cost is not None and observed_cost > 0 else 0.0
                    issue = "Lambda has no observed invocations" if inactive else "Lambda Memory Over-provisioned"
                    recommendation = (
                        "No invocations were observed during the metric window. Review the trigger and schedule, then disable or remove the function if it is not required."
                        if inactive else
                        f"Function allocated {allocated_mb}MB but observed usage is ~{used_mb}MB. Test a lower AWS memory setting, confirm latency/error limits, and compare the resulting GB-second charge in AWS."
                    )
                    findings.append(
                        make_finding(
                            tenant_id=ctx.tenant_id,
                            resource_id=fn_name,
                            resource_type="lambda",
                            severity="medium",
                            category=self.category,
                            issue=issue,
                            recommendation=recommendation,
                            confidence="high",
                            estimated_monthly_waste=round(monthly_stop_saving, 8),
                            window_days=14.0,
                            aws_account_id=account_id,
                            region=region,
                            evidence=f"Configured memory={allocated_mb if allocated_mb is not None else 'No data available'}MB; observed memory={used_mb if used_mb is not None else 'No data available'}MB; observed invocations={invocations if invocations is not None else 'No data available'} across {fn.get('metric_samples', 0)} samples. {cost_evidence} Projected monthly disable savings: ${monthly_stop_saving:.8f} when supported by observed resource cost.",
                            observed_cost=observed_cost,
                        )
                    )
        return findings


RULE = LambdaOptimizationRule()
