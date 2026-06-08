"""Static instance cost lookup (Feature 2).

Approximate on-demand USD/month for common instance types. We deliberately do
NOT call the AWS Pricing API yet (Sprint 2 scope). Extend this table as needed.
"""

INSTANCE_COSTS = {
    "t3.micro": 8.5,
    "t3.small": 17.0,
    "t3.medium": 34.0,
    "t3.large": 68.0,
    "t3.xlarge": 136.0,
    "t3.2xlarge": 272.0,
    "t2.micro": 8.5,
    "t2.small": 17.0,
    "t2.medium": 34.0,
    "m5.large": 70.0,
    "m5.xlarge": 140.0,
    "c5.large": 62.0,
    "c5.xlarge": 124.0,
}


def estimate_monthly_cost(instance_type: str | None) -> float:
    """Estimated monthly waste for an idle instance == its full monthly cost.

    Unknown instance types return 0 (we never guess pricing we don't have).
    """
    if not instance_type:
        return 0.0
    return INSTANCE_COSTS.get(instance_type, 0.0)
