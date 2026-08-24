import uuid
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Float, String, UniqueConstraint

from .connection import Base


class CostRecord(Base):
    __tablename__ = "aws_costs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    aws_account_id = Column(String, nullable=False, index=True, default="241524041973")
    billing_date = Column(Date, nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    region = Column(String, nullable=False, index=True, default="us-east-2")
    usage_type = Column(String, nullable=False, default="BoxUsage:t3.medium")
    unblended_cost = Column(Float, nullable=False, default=0.0)
    amortized_cost = Column(Float, nullable=False, default=0.0)
    currency = Column(String, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "aws_account_id",
            "billing_date",
            "service_name",
            "region",
            "usage_type",
            name="uq_aws_costs_tenant_billing",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "aws_account_id": self.aws_account_id,
            "billing_date": self.billing_date.isoformat() if self.billing_date else None,
            "service_name": self.service_name,
            "region": self.region,
            "usage_type": self.usage_type,
            "unblended_cost": float(self.unblended_cost),
            "amortized_cost": float(self.amortized_cost),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
