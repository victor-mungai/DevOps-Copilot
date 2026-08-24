from typing import Any


SERVICE_NAME_MAP = {
    "amazonec2": "EC2",
    "amazon ec2": "EC2",
    "ec2": "EC2",
    "amazonrds": "RDS",
    "amazon relational database service": "RDS",
    "rds": "RDS",
    "awslambda": "Lambda",
    "aws lambda": "Lambda",
    "lambda": "Lambda",
    "amazons3": "S3",
    "amazon simple storage service": "S3",
    "s3": "S3",
    "amazondynamodb": "DynamoDB",
    "dynamodb": "DynamoDB",
    "amazoncloudwatch": "CloudWatch",
    "cloudwatch": "CloudWatch",
    "awselasticloadbalancing": "ELB",
    "elb": "ELB",
}


def normalize_service_name(raw_name: str) -> str:
    if not raw_name:
        return "Other"
    clean = raw_name.strip().lower()
    return SERVICE_NAME_MAP.get(clean, raw_name.strip())


def normalize_cost_entry(
    tenant_id: str,
    aws_account_id: str,
    billing_date: str,
    raw_service: str,
    region: str,
    usage_type: str,
    unblended_cost: float,
    amortized_cost: float | None = None,
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "aws_account_id": aws_account_id or "241524041973",
        "billing_date": billing_date,
        "service_name": normalize_service_name(raw_service),
        "region": region or "us-east-2",
        "usage_type": usage_type or "GeneralUsage",
        "unblended_cost": round(float(unblended_cost or 0.0), 4),
        "amortized_cost": round(float(amortized_cost if amortized_cost is not None else unblended_cost or 0.0), 4),
        "currency": "USD",
    }
