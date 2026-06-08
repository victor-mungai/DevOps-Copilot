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
        existing.severity = data["severity"]
        existing.recommendation = data["recommendation"]
        existing.confidence = data["confidence"]
        existing.estimated_monthly_waste = data["estimated_monthly_waste"]
        existing.avg_cpu = data.get("avg_cpu")
        existing.instance_type = data.get("instance_type")
        existing.window_days = data.get("window_days")
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
