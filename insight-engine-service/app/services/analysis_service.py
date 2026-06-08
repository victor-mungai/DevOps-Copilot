import logging

from sqlalchemy.orm import Session

from .. import config
from ..db import insight_repository
from ..rules import idle_ec2
from ..sources.provider import get_provider

logger = logging.getLogger("insight-engine")


def analyze_tenant(db: Session, tenant_id: str, request_id: str = "-") -> list[dict]:
    """Run the idle-EC2 rule for every EC2 instance owned by a tenant.

    Flow: authoritative EC2 list -> per-instance CPU aggregate over the window
    -> rule -> cost estimate -> persist. Everything is tenant-scoped. The data
    source (Prometheus+aws-connector vs offline dev seed) is chosen by config.
    """
    assert tenant_id, "tenant_id is required"  # Feature 6: tenant isolation

    provider = get_provider()
    instances = provider.list_ec2_instances(tenant_id)
    logger.info(
        "Analyzing tenant",
        extra={
            "tenant_id": tenant_id,
            "request_id": request_id,
            "service": "insight-engine",
            "endpoint": "analyze",
            "ec2_count": len(instances),
        },
    )

    insights: list[dict] = []
    for inst in instances:
        instance_id = inst["instance_id"]
        agg = provider.avg_cpu_over_window(
            tenant_id, instance_id, config.IDLE_WINDOW_DAYS
        )
        if not agg:
            continue  # no metrics for this instance yet

        finding = idle_ec2.evaluate(
            tenant_id=tenant_id,
            instance_id=instance_id,
            instance_type=inst.get("instance_type"),
            avg_cpu=agg["avg"],
            samples=agg["samples"],
        )
        if finding:
            stored = insight_repository.upsert_insight(db, finding)
            insights.append(stored.to_dict())

    logger.info(
        "Analysis complete",
        extra={
            "tenant_id": tenant_id,
            "request_id": request_id,
            "service": "insight-engine",
            "endpoint": "analyze",
            "insights_found": len(insights),
        },
    )
    return insights
