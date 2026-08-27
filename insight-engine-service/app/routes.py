import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
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
    header_tenant = getattr(request.state, "tenant_id", None) or request.headers.get("X-Tenant-ID")
    if header_tenant and header_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch",
        )
    if not header_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )


@router.get("/health")
def health():
    return {"status": "healthy", "service": "insight-engine"}


@router.get("/rag/diagnostics")
def rag_diagnostics(request: Request, x_tenant_id: str | None = Header(None)):
    tenant_id = getattr(request.state, "tenant_id", None) or x_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    from .services import rag_service
    return rag_service.diagnostics(tenant_id)


@router.get("/insights/coverage")
def get_analysis_coverage(
    request: Request,
    region: str | None = None,
    db: Session = Depends(get_db),
    x_tenant_id: str | None = Header(None),
):
    """Return tenant-scoped analysis coverage from live AWS resource discovery."""
    t_id = getattr(request.state, "tenant_id", None) or x_tenant_id
    if not t_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    from .sources.provider import get_provider
    from .services.canonical_resource import get_canonical_resource

    provider = get_provider()
    instances = provider.list_ec2_instances(t_id, region=region)
    rds_dbs = provider.list_rds_databases(t_id, region=region)
    lambda_fns = provider.list_lambda_functions(t_id, region=region)

    all_insights = insight_repository.list_insights(db, t_id, limit=500)
    flagged_resources = {ins.resource_id: ins for ins in all_insights if ins.status == "active"}
    healthy_resources = {ins.resource_id: ins for ins in all_insights if ins.status == "healthy"}

    resources_detail = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    no_data_count = 0

    for inst in instances:
        rid = inst["instance_id"]
        c_res = get_canonical_resource(
            rid,
            "ec2",
            tags=inst.get("tags"),
            region=inst.get("region") or region,
            account_id=inst.get("account_id"),
        )
        ins = flagged_resources.get(rid)
        healthy_ins = healthy_resources.get(rid)
        if ins:
            health_st = "critical" if ins.severity == "high" else "warning"
            if health_st == "critical":
                critical_count += 1
            else:
                warning_count += 1
        elif healthy_ins:
            health_st = "healthy"
            healthy_count += 1
        else:
            health_st = "no_data"
            no_data_count += 1

        resources_detail.append({
            "resource_id": rid,
            "display_name": c_res["display_name"],
            "resource_type": "EC2",
            "metrics_available": False,
            "metrics_status": "No data available" if not ins else "available",
            "rules_evaluated": len(__import__("app.rules.registry", fromlist=["get_rules"]).get_rules()),
            "insights_count": 1 if ins else 0,
            "insight_status": "finding" if ins else ("Healthy / No issues detected" if healthy_ins else "No analysis data available"),
            "evaluation_status": "evaluated" if (ins or healthy_ins) else "not_evaluated",
            "health_state": health_st,
            "account_id": c_res["account_id"],
            "region": c_res["region"],
        })

    for db_inst in rds_dbs:
        rid = db_inst.get("resource_id") or db_inst.get("DBInstanceIdentifier")
        if not rid:
            continue
        c_res = get_canonical_resource(
            rid,
            "rds",
            raw_name=rid,
            region=db_inst.get("region") or region,
            account_id=db_inst.get("account_id"),
        )
        ins = flagged_resources.get(rid)
        healthy_ins = healthy_resources.get(rid)
        if ins:
            health_st = "critical" if ins.severity == "high" else "warning"
            if health_st == "critical":
                critical_count += 1
            else:
                warning_count += 1
        elif healthy_ins:
            health_st = "healthy"
            healthy_count += 1
        else:
            health_st = "no_data"
            no_data_count += 1

        resources_detail.append({
            "resource_id": rid,
            "display_name": c_res["display_name"],
            "resource_type": "RDS",
            "metrics_available": False,
            "metrics_status": "No data available" if not ins else "available",
            "rules_evaluated": len(__import__("app.rules.registry", fromlist=["get_rules"]).get_rules()),
            "insights_count": 1 if ins else 0,
            "insight_status": "finding" if ins else ("Healthy / No issues detected" if healthy_ins else "No analysis data available"),
            "evaluation_status": "evaluated" if (ins or healthy_ins) else "not_evaluated",
            "health_state": health_st,
            "account_id": c_res["account_id"],
            "region": c_res["region"],
        })

    for fn in lambda_fns:
        rid = fn.get("resource_id") or fn.get("function_name")
        if not rid:
            continue
        c_res = get_canonical_resource(
            rid,
            "lambda",
            raw_name=rid,
            region=fn.get("region") or region,
            account_id=fn.get("account_id"),
        )
        ins = flagged_resources.get(rid)
        healthy_ins = healthy_resources.get(rid)
        if ins:
            health_st = "warning"
            warning_count += 1
        elif healthy_ins:
            health_st = "healthy"
            healthy_count += 1
        else:
            health_st = "no_data"
            no_data_count += 1

        resources_detail.append({
            "resource_id": rid,
            "display_name": c_res["display_name"],
            "resource_type": "LAMBDA",
            "metrics_available": False,
            "metrics_status": "No data available" if not ins else "available",
            "rules_evaluated": len(__import__("app.rules.registry", fromlist=["get_rules"]).get_rules()),
            "insights_count": 1 if ins else 0,
            "insight_status": "finding" if ins else ("Healthy / No issues detected" if healthy_ins else "No analysis data available"),
            "evaluation_status": "evaluated" if (ins or healthy_ins) else "not_evaluated",
            "health_state": health_st,
            "account_id": c_res["account_id"],
            "region": c_res["region"],
        })

    total = len(resources_detail)
    analyzed = total if total else 0
    with_insights = len([r for r in resources_detail if r["insights_count"] > 0])

    return {
        "tenant_id": t_id,
        "total_resources": total,
        "resources_with_metrics": len([r for r in resources_detail if r["metrics_available"]]),
        "resources_analyzed": analyzed,
        "resources_with_insights": with_insights,
        "resources_without_insights": max(0, total - with_insights),
        "coverage_percent": round((analyzed / total) * 100, 2) if total else 0,
        "health_summary": {
            "healthy": healthy_count,
            "warning": warning_count,
            "critical": critical_count,
            "no_data": no_data_count,
        },
        "resources": resources_detail,
    }


@router.post("/insights/{tenant_id}/analyze")
def analyze(
    tenant_id: str, request: Request, region: str = "", async_mode: bool = True, db: Session = Depends(get_db)
):
    _enforce_tenant(request, tenant_id)
    if not async_mode:
        try:
            insights = analyze_tenant(
                db, tenant_id, region=region or None, request_id=get_request_id(request)
            )
            return AnalyzeResponse(
                tenant_id=tenant_id, insights_found=len(insights), insights=insights
            )
        except ConnectorError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AWS connector is unavailable.",
            ) from exc

    # Asynchronous Job Mode
    import uuid
    from datetime import datetime
    from shared.messaging import publish
    from .db.models import Job

    job = Job(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        job_type="insight_analysis",
        status="queued",
        created_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    publish(
        event_type="insight.analysis.requested",
        tenant_id=tenant_id,
        source="insight-api",
        region=region or "",
        payload={"job_id": job.id}
    )

    # In local queue fallback mode, trigger processing thread directly
    from shared.messaging.connection import get_messaging_manager
    manager = get_messaging_manager()
    if not manager.is_connected:
        from .workers.insight_worker import process_analysis_job
        import threading
        event_payload = {
            "tenant_id": tenant_id,
            "region": region or "",
            "payload": {"job_id": job.id}
        }
        threading.Thread(target=process_analysis_job, args=(event_payload,), daemon=True).start()

    return {
        "job_id": job.id,
        "tenant_id": tenant_id,
        "status": "queued",
        "message": "Analysis job queued successfully",
        "insights_found": 0,
        "insights": []
    }


@router.get("/insights/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    from .db.models import Job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.get("/insights")
def list_all_insights(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    from .db.models import InsightRecord
    rows = db.query(InsightRecord).order_by(InsightRecord.created_at.desc()).offset(offset).limit(limit).all()
    return [row.to_dict() for row in rows]


@router.get("/insights/{tenant_id}", response_model=list)
def list_tenant_insights(
    tenant_id: str,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if tenant_id.lower() in ["all", "all-accounts", "all_accounts"]:
        return list_all_insights(limit=limit, offset=offset, db=db)
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
        context,
        payload.question,
        history=history,
        request_id=get_request_id(request),
        model=payload.model,
        api_key=payload.api_key,
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
