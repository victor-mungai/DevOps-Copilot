"""Security: security groups open to 0.0.0.0/0. Ready; produces findings once the
connector exposes security groups (ctx.security_groups)."""
from ..base import AnalysisContext, make_finding

SENSITIVE_PORTS = {22, 3389, 3306, 5432, 6379, 27017}


class PublicSecurityGroupsRule:
    id = "security.public_security_groups"
    category = "security"
    name = "Public Security Groups"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for sg in ctx.security_groups:
            open_ports = [p for p in sg.get("open_to_world_ports", []) if p in SENSITIVE_PORTS]
            if not open_ports:
                continue
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=sg.get("group_id", "unknown"),
                    resource_type="security_group",
                    severity="high",
                    category=self.category,
                    issue=f"Security group open to the internet on {open_ports}",
                    recommendation="Restrict ingress to known CIDRs; never expose admin/db ports to 0.0.0.0/0.",
                    confidence="high",
                )
            )
        return findings


RULE = PublicSecurityGroupsRule()
