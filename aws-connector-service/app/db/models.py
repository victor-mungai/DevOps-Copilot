import uuid

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .connection import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(255))
    external_id = Column(String(255), nullable=False)
    created_at = Column(DateTime)


class AwsAccount(Base):
    __tablename__ = "aws_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(String(20))
    role_arn = Column(Text, nullable=False)
    region = Column(String(50))
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime)
    last_verified_at = Column(DateTime)
