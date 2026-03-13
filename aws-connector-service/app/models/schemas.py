from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AwsResourceResponse(BaseModel):
    data: dict


class AwsClientRequest(BaseModel):
    region: Optional[str] = Field(default=None)


class CloudWatchMetricRequest(BaseModel):
    namespace: str
    metric_name: str
    dimensions: list[dict]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    period: int = 60
    statistics: list[str] = Field(default_factory=lambda: ["Average"])
    region: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
