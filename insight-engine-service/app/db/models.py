import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String

from .connection import Base


class Insight(Base):
    __tablename__ = "insights"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True, default="us-east-2")
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=True)
    issue = Column(String, nullable=False)
    description = Column(String, nullable=True)
    evidence = Column(String, nullable=True)
    recommendation = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    confidence = Column(String, nullable=False, default="high")
    estimated_monthly_waste = Column(Float, nullable=False, default=0.0)
    avg_cpu = Column(Float, nullable=True)
    instance_type = Column(String, nullable=True)
    window_days = Column(Float, nullable=True)
    first_detected_at = Column(DateTime, default=datetime.utcnow)
    last_detected_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    occurrence_count = Column(Float, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "region": self.region,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "severity": self.severity,
            "category": self.category,
            "title": self.title or self.issue,
            "issue": self.issue,
            "description": self.description or self.issue,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "status": self.status,
            "confidence": self.confidence,
            "estimated_monthly_waste": self.estimated_monthly_waste,
            "avg_cpu": self.avg_cpu,
            "instance_type": self.instance_type,
            "window_days": self.window_days,
            "first_detected_at": self.first_detected_at.isoformat() if self.first_detected_at else None,
            "last_detected_at": self.last_detected_at.isoformat() if self.last_detected_at else None,
            "occurrence_count": self.occurrence_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
