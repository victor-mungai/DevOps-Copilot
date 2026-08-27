"""Security: public S3 buckets. Ready; produces findings once the connector
exposes bucket ACL/policy info (ctx.s3)."""
from ..base import AnalysisContext, make_finding


class PublicS3Rule:
    id = "security.public_s3"
    category = "security"
    name = "Public S3 Buckets"

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        findings: list[dict] = []
        for bucket in ctx.s3:
            if not bucket.get("public"):
                continue
            findings.append(
                make_finding(
                    tenant_id=ctx.tenant_id,
                    resource_id=bucket.get("name", "unknown"),
                    resource_type="s3",
                    severity="high",
                    category=self.category,
                    issue="Publicly accessible S3 bucket",
                    recommendation="Enable Block Public Access and review the bucket policy/ACL.",
                    confidence="high",
                )
            )
        return findings


RULE = PublicS3Rule()
