from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AwsResourceResponse(BaseModel):
    data: dict


class AwsClientRequest(BaseModel):
    region: Optional[str] = Field(default=None)
    account_id: Optional[str] = Field(default=None)


class CloudWatchMetricRequest(BaseModel):
    namespace: str
    metric_name: str
    dimensions: list[dict]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    period: int = 60
    statistics: list[str] = Field(default_factory=lambda: ["Average"])
    region: Optional[str] = None
    account_id: Optional[str] = None


class CostAndUsageRequest(BaseModel):
    start_date: str
    end_date: str
    granularity: str = "DAILY"
    metrics: list[str] = Field(default_factory=lambda: ["UnblendedCost", "AmortizedCost"])
    group_by: list[dict] = Field(
        default_factory=lambda: [
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "REGION"},
        ]
    )
    account_id: Optional[str] = None


class ResourceCostRequest(BaseModel):
    """AWS Cost Explorer resource-level attribution request.

    Cost Explorer currently exposes this data for a limited set of services and
    recent periods. The caller must treat an empty result as unavailable data.
    """
    start_date: str
    end_date: str
    metrics: list[str] = Field(default_factory=lambda: ["UnblendedCost", "NetUnblendedCost"])
    account_id: Optional[str] = None
    granularity: str = "DAILY"


class ErrorResponse(BaseModel):
    detail: str
