"""Compliance: EC2 instances missing required tags (real — uses instance tags)."""
import os

from ..base import AnalysisContext, make_finding

REQUIRED_TAGS = [t.strip() for t in os.getenv("REQUIRED_TAGS", "Name").split(",") if t.strip()]


class MissingTagsRule:
    id = "compliance.missing_tags"
    category = "compliance"
    name = "Missing Required Tags"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for s in ctx.ec2:
            present = {k for k in s.tags.keys()}
            missing = [t for t in REQUIRED_TAGS if t not in present]
            if not missing:
                continue
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=s.resource_id,
                    resource_type="ec2",
                    severity="low",
                    category=self.category,
                    issue=f"Missing required tag(s): {', '.join(missing)}",
                    recommendation="Add the required tags for ownership, cost allocation and governance.",
                    confidence="high",
                    instance_type=s.instance_type,
                )
            )
        return findings


RULE = MissingTagsRule()
