import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import insight_repository
from .db.connection import get_db
from .models.schemas import AnalyzeResponse, ExplainRequest, ExplainResponse
from .observability import get_request_id
from .services import llm_service
from .services.analysis_service import analyze_tenant
from .services.context_builder import build_ai_context
from .sources.aws_connector_client import ConnectorError

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
def analyze(
    tenant_id: str, request: Request, region: str = "", db: Session = Depends(get_db)
):
    _enforce_tenant(request, tenant_id)
    try:
        insights = analyze_tenant(
            db, tenant_id, region=region or None, request_id=get_request_id(request)
        )
    except ConnectorError as exc:
        logger.warning("Connector unavailable during analyze: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AWS connector is unavailable. Ensure the aws-connector "
            "service is running and the account is connected.",
        ) from exc
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

    # Sprint 2.1: build the full tenant-scoped context (insights + live metrics +
    # region + RAG) and answer with a bounded sliding window of history.
    context = build_ai_context(
        db,
        tenant_id,
        region=payload.region,
        resource_id=payload.resource_id,
        insight_id=payload.insight_id,
        query=payload.question,
    )
    history = [m.model_dump() for m in payload.history]
    result = llm_service.explain(
        context, payload.question, history=history, request_id=get_request_id(request)
    )
    primary = context.get("primary_insight") or {}
    return ExplainResponse(
        answer=result["answer"],
        model=result["model"],
        insight_id=context.get("primary_insight_id"),
        confidence=primary.get("confidence"),
        related_incidents=[
            {
                "resource_id": i["resource_id"],
                "issue": i["issue"],
                "severity": i["severity"],
                "category": i["category"],
            }
            for i in context.get("related_incidents", [])
        ],
        sources=context.get("sources", []),
        rag_enabled=context.get("rag_enabled", False),
    )
