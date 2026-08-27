import os
from ..base import AnalysisContext, Rule, make_finding

HIGH_MEMORY_THRESHOLD = float(os.getenv("RULE_HIGH_MEMORY_THRESHOLD", "85.0"))


class HighMemoryRule:
    id = "perf_high_memory"
    category = "performance"
    name = "High Sustained Memory Usage"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings = []
        for signal in ctx.ec2:
            # Memory signal check if present in tags or context
            mem_val = signal.tags.get("memory_utilization") if isinstance(signal.tags, dict) else None
            if mem_val is not None and float(mem_val) >= HIGH_MEMORY_THRESHOLD:
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=signal.resource_id,
                        resource_type="ec2",
                        severity="high",
                        category=self.category,
                        issue=f"Resource {signal.resource_id} is operating near memory capacity ({float(mem_val):.1f}%)",
                        recommendation="Increase instance memory allocation or optimize heap/memory buffers to prevent OOM termination.",
                        confidence="high",
                        instance_type=signal.instance_type,
                    )
                )
        return findings


RULE: Rule = HighMemoryRule()
