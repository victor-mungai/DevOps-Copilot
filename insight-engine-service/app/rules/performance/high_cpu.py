"""Performance: sustained high CPU (real — uses the same CPU aggregate)."""
import os

from ..base import AnalysisContext, make_finding

HIGH_CPU_THRESHOLD = float(os.getenv("HIGH_CPU_THRESHOLD", "85.0"))
MIN_SAMPLES = int(os.getenv("IDLE_MIN_SAMPLES", "60"))


class HighCpuRule:
    id = "performance.high_cpu"
    category = "performance"
    name = "High CPU Utilization"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for s in ctx.ec2:
            if s.avg_cpu is None or s.samples < MIN_SAMPLES:
                continue
            if s.avg_cpu < HIGH_CPU_THRESHOLD:
                continue
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=s.resource_id,
                    resource_type="ec2",
                    severity="high",
                    category=self.category,
                    issue="Sustained High CPU Utilization",
                    recommendation="Investigate load; scale up/out or optimize the workload.",
                    confidence="high",
                    avg_cpu=round(s.avg_cpu, 2),
                    instance_type=s.instance_type,
                )
            )
        return findings


RULE = HighCpuRule()
