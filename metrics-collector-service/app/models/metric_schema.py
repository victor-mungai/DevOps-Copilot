from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class Metric(BaseModel):
    tenant_id: str
    resource_id: str
    metric_name: str
    timestamp: datetime
    value: float
    aws_account_id: str = "default"
    region: str = "us-east-2"
    resource_type: str = "ec2"
    labels: Dict[str, str] = Field(default_factory=dict)


class CollectRequest(BaseModel):
    tenant_ids: Optional[list[str]] = None
