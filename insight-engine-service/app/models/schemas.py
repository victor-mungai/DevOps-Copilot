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


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=4000)


class ExplainRequest(BaseModel):
    # Feature 7: request validation via Pydantic.
    question: str = Field(..., min_length=1, max_length=2000)
    insight_id: Optional[str] = None
    session_id: Optional[str] = None
    # Sprint 2.1: region + resource focus + sliding-window conversation history.
    region: Optional[str] = None
    resource_id: Optional[str] = None
    history: list[ChatMessage] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    answer: str
    model: str
    insight_id: Optional[str] = None
