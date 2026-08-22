"""Compliance: unencrypted volumes/buckets. Ready; needs encryption flags from
the connector (EBS Encrypted / S3 default encryption), not collected yet."""
from ..base import AnalysisContext, make_finding


class MissingEncryptionRule:
    id = "compliance.missing_encryption"
    category = "compliance"
    name = "Missing Encryption"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for vol in ctx.ebs:
            if vol.get("encrypted") is False:
                findings.append(
                    make_finding(
                        tenant_id=ctx.tenant_id,
                        resource_id=vol.get("volume_id", "unknown"),
                        resource_type="ebs",
                        severity="medium",
                        category=self.category,
                        issue="Unencrypted EBS volume",
                        recommendation="Enable encryption (re-create from an encrypted snapshot).",
                        confidence="high",
                    )
                )
        return findings


RULE = MissingEncryptionRule()
