import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import insight_repository
from .db.connection import get_db
from .models.schemas import AnalyzeResponse, ExplainRequest, ExplainResponse
from .observability import get_request_id
from .services import llm_service
from .services.analysis_service import analyze_tenant

logger = logging.getLogger("insight-engine")
router = APIRouter()


def _enforce_tenant(request: Request, tenant_id: str) -> None:
    """Feature 6: a path tenant_id must match the gateway-injected identity."""
    header_tenant = getattr(request.state, "tenant_id", None)
    if header_tenant and header_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch",
        )


@router.get("/health")
def health():
    return {"status": "healthy", "service": "insight-engine"}


@router.post("/insights/{tenant_id}/analyze", response_model=AnalyzeResponse)
def analyze(tenant_id: str, request: Request, db: Session = Depends(get_db)):
    _enforce_tenant(request, tenant_id)
    insights = analyze_tenant(db, tenant_id, request_id=get_request_id(request))
    return AnalyzeResponse(
        tenant_id=tenant_id, insights_found=len(insights), insights=insights
    )


@router.get("/insights/{tenant_id}", response_model=list)
def list_tenant_insights(
    tenant_id: str,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    _enforce_tenant(request, tenant_id)
    rows = insight_repository.list_insights(db, tenant_id, limit=limit, offset=offset)
    return [row.to_dict() for row in rows]


@router.post("/insights/{tenant_id}/explain", response_model=ExplainResponse)
def explain(
    tenant_id: str,
    payload: ExplainRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_tenant(request, tenant_id)

    if payload.insight_id:
        insight = insight_repository.get_insight(db, tenant_id, payload.insight_id)
    else:
        # Default to the most recent insight so the chat works without an id.
        rows = insight_repository.list_insights(db, tenant_id, limit=1)
        insight = rows[0] if rows else None

    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No insight found for tenant",
        )

    result = llm_service.explain_insight(
        insight.to_dict(), payload.question, request_id=get_request_id(request)
    )
    return ExplainResponse(
        answer=result["answer"], model=result["model"], insight_id=insight.id
    )
