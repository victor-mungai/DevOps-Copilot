from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Insight


def upsert_insight(db: Session, data: dict) -> Insight:
    assert data.get("tenant_id"), "tenant_id is required"

    existing = db.execute(
        select(Insight)
        .where(Insight.tenant_id == data["tenant_id"])
        .where(Insight.resource_id == data["resource_id"])
        .where(Insight.issue == data["issue"])
        .order_by(Insight.created_at.desc())
    ).scalars().first()

    if existing:
        existing.last_detected_at = datetime.utcnow()
        existing.occurrence_count = (existing.occurrence_count or 1) + 1
        existing.severity = data.get("severity", existing.severity)
        existing.recommendation = data.get("recommendation", existing.recommendation)
        existing.confidence = data.get("confidence", existing.confidence)
        existing.estimated_monthly_waste = data.get("estimated_monthly_waste", existing.estimated_monthly_waste)
        existing.aws_account_id = data.get("aws_account_id", existing.aws_account_id)
        existing.region = data.get("region", existing.region)
        existing.evidence = data.get("evidence", existing.evidence)
        existing.avg_cpu = data.get("avg_cpu", existing.avg_cpu)
        existing.instance_type = data.get("instance_type", existing.instance_type)
        existing.window_days = data.get("window_days", existing.window_days)
        existing.observed_cost = data.get("observed_cost", existing.observed_cost)
        existing.inactive_hours = data.get("inactive_hours", existing.inactive_hours)
        db.commit()
        db.refresh(existing)
        return existing

    insight = Insight(**data)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


def list_insights(db: Session, tenant_id: str, limit: int = 50, offset: int = 0):
    assert tenant_id, "tenant_id is required"
    limit = max(1, min(limit, 200))
    return db.execute(
        select(Insight)
        .where(Insight.tenant_id == tenant_id)
        .order_by(Insight.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()


def get_insight(db: Session, tenant_id: str, insight_id: str):
    assert tenant_id, "tenant_id is required"
    return db.execute(
        select(Insight)
        .where(Insight.tenant_id == tenant_id)
        .where(Insight.id == insight_id)
    ).scalars().first()
