from typing import Optional

from pydantic import BaseModel, Field


class InsightOut(BaseModel):
    id: str
    tenant_id: str
    resource_id: str
    resource_type: str
    severity: str
    category: str
    issue: str
    recommendation: str
    confidence: str
    estimated_monthly_waste: float
    avg_cpu: Optional[float] = None
    instance_type: Optional[str] = None
    window_days: Optional[float] = None
    created_at: Optional[str] = None


class AnalyzeResponse(BaseModel):
    tenant_id: str
    insights_found: int
    insights: list[InsightOut]


class ExplainRequest(BaseModel):
    # Feature 7: request validation via Pydantic.
    question: str = Field(..., min_length=1, max_length=2000)
    insight_id: Optional[str] = None
    session_id: Optional[str] = None


class ExplainResponse(BaseModel):
    answer: str
    model: str
    insight_id: Optional[str] = None
