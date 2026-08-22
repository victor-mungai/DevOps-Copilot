from fastapi import APIRouter, HTTPException

from .models.metric_schema import CollectRequest
from .services.metrics_service import collect_for_tenant, collect_for_tenants

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/collect/tenant/{tenant_id}")
async def collect_tenant(tenant_id: str):
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        metrics = collect_for_tenant(tenant_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"tenant_id": tenant_id, "count": len(metrics)}


@router.post("/collect/run")
async def collect_run(payload: CollectRequest):
    if not payload.tenant_ids:
        raise HTTPException(status_code=400, detail="tenant_ids are required")
    try:
        results = collect_for_tenants(payload.tenant_ids)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"results": results}
