import os
from ..base import AnalysisContext, Rule, make_finding

HIGH_CPU_THRESHOLD = float(os.getenv("RULE_HIGH_CPU_THRESHOLD", "80.0"))


class SustainedCpuRule:
    id = "perf_sustained_cpu"
    category = "performance"
    name = "High Sustained CPU Utilization"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings = []
        for signal in ctx.ec2:
            if signal.avg_cpu is not None and signal.avg_cpu >= HIGH_CPU_THRESHOLD:
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=signal.resource_id,
                        resource_type="ec2",
                        severity="high",
                        category=self.category,
                        issue=f"EC2 instance {signal.resource_id} is experiencing high sustained CPU ({signal.avg_cpu:.1f}%) above {HIGH_CPU_THRESHOLD:.0f}% threshold",
                        recommendation="Investigate active processes, review workload scaling policies, or upgrade instance family.",
                        confidence="high",
                        avg_cpu=signal.avg_cpu,
                        instance_type=signal.instance_type,
                    )
                )
        return findings


RULE: Rule = SustainedCpuRule()
