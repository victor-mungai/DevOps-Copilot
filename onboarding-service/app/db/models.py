import datetime as dt
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .connection import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class AwsAccount(Base):
    __tablename__ = "aws_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    account_id = Column(String(20))
    role_arn = Column(Text, nullable=False)
    region = Column(String(50))
    status = Column(String(50), default="pending", nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)


class WorkspaceUser(Base):
    """Tenant-scoped workspace membership. Authentication remains owned by the auth provider."""

    __tablename__ = "workspace_users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_workspace_users_tenant_email"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(320), nullable=False)
    role = Column(String(30), nullable=False, default="member")
    status = Column(String(30), nullable=False, default="invited")
    auth_user_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)
