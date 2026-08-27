from typing import Literal, Optional

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
    observed_cost: Optional[float] = None
    inactive_hours: Optional[float] = None
    aws_account_id: Optional[str] = None
    region: Optional[str] = None
    evidence: Optional[str] = None
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
    model: Literal["auto", "chatgpt", "claude"] = "auto"
    api_key: Optional[str] = Field(default=None, min_length=10, max_length=500)


class RelatedIncident(BaseModel):
    resource_id: str
    issue: str
    severity: str
    category: str


class Source(BaseModel):
    source: Optional[str] = None
    score: Optional[float] = None
    resource_id: Optional[str] = None


class ExplainResponse(BaseModel):
    answer: str
    model: str
    insight_id: Optional[str] = None
    confidence: Optional[str] = None
    related_incidents: list[RelatedIncident] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    rag_enabled: bool = False
