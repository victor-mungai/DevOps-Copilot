import uuid
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Numeric, String, UniqueConstraint

from .connection import Base


class CostRecord(Base):
    __tablename__ = "aws_costs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    aws_account_id = Column(String, nullable=False, index=True)
    billing_date = Column(Date, nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True, index=True)
    usage_type = Column(String, nullable=True)
    record_type = Column(String, nullable=True, index=True)
    unblended_cost = Column(Numeric(18, 8), nullable=False, default=0.0)
    amortized_cost = Column(Numeric(18, 8), nullable=False, default=0.0)
    net_unblended_cost = Column(Numeric(18, 8), nullable=False, default=0.0)
    net_amortized_cost = Column(Numeric(18, 8), nullable=False, default=0.0)
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
            "record_type",
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
            "record_type": self.record_type,
            "unblended_cost": float(self.unblended_cost or 0.0),
            "amortized_cost": float(self.amortized_cost or 0.0),
            "net_unblended_cost": float(self.net_unblended_cost or 0.0),
            "net_amortized_cost": float(self.net_amortized_cost or 0.0),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CostSyncLog(Base):
    __tablename__ = "cost_sync_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    aws_account_id = Column(String, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="SUCCESS")


class ResourceCostRecord(Base):
    """A Cost Explorer resource attribution record; never a derived allocation."""
    __tablename__ = "aws_resource_costs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    aws_account_id = Column(String, nullable=False, index=True)
    billing_date = Column(Date, nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True, index=True)
    resource_id = Column(String, nullable=False, index=True)
    unblended_cost = Column(Numeric(18, 8), nullable=False, default=0.0)
    net_unblended_cost = Column(Numeric(18, 8), nullable=False, default=0.0)
    currency = Column(String, default="USD")
    source = Column(String, nullable=False, default="AWS_COST_EXPLORER_GET_COST_AND_USAGE_WITH_RESOURCES")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "aws_account_id", "billing_date", "service_name", "region", "resource_id",
            name="uq_aws_resource_costs_scope",
        ),
    )
