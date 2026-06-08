from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class Metric(BaseModel):
    tenant_id: str
    resource_id: str
    metric_name: str
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class CollectRequest(BaseModel):
    tenant_ids: Optional[list[str]] = None
