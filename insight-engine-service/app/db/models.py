import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String

from .connection import Base


class Insight(Base):
    __tablename__ = "insights"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    category = Column(String, nullable=False)
    issue = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    estimated_monthly_waste = Column(Float, nullable=False, default=0.0)
    avg_cpu = Column(Float, nullable=True)
    instance_type = Column(String, nullable=True)
    window_days = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "severity": self.severity,
            "category": self.category,
            "issue": self.issue,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "estimated_monthly_waste": self.estimated_monthly_waste,
            "avg_cpu": self.avg_cpu,
            "instance_type": self.instance_type,
            "window_days": self.window_days,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
