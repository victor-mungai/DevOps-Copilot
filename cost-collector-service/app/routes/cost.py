from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.connection import get_db
from ..messaging.events import request_cost_collection
from ..services.cost_collection import (
    get_cost_anomalies,
    get_cost_by_account,
    get_cost_by_region,
    get_cost_by_service,
    get_cost_summary,
    get_cost_trend,
    ingest_cost_records,
)

router = APIRouter()


def _extract_tenant(x_tenant_id: Optional[str] = Header(None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    return x_tenant_id


@router.get("/cost/summary")
def summary(
    range: str = Query("30d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_summary(db, tenant_id=tenant_id, range_days=days)


@router.get("/cost/trend")
def trend(
    range: str = Query("30d"),
    granularity: str = Query("daily"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_trend(db, tenant_id=tenant_id, range_days=days, granularity=granularity)


@router.get("/cost/services")
def services(
    range: str = Query("30d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_by_service(db, tenant_id=tenant_id, range_days=days)


@router.get("/cost/regions")
def regions(
    range: str = Query("30d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_by_region(db, tenant_id=tenant_id, range_days=days)


@router.get("/cost/accounts")
def accounts(
    range: str = Query("30d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_by_account(db, tenant_id=tenant_id, range_days=days)


@router.get("/cost/forecast")
def forecast(
    range: str = Query("30d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    summary_data = get_cost_summary(db, tenant_id=tenant_id, range_days=30)
    return {
        "tenant_id": tenant_id,
        "projected_monthly": summary_data["projected_monthly"],
        "confidence": "high",
        "currency": "USD",
    }


@router.get("/cost/anomalies")
def anomalies(
    range: str = Query("30d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_anomalies(db, tenant_id=tenant_id, range_days=days)


@router.post("/cost/collect")
def trigger_collect(
    region: str = Query("us-east-2"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    # Ingest synchronous records and emit asynchronous event
    count = ingest_cost_records(db, tenant_id=tenant_id, days=90)
    event_data = request_cost_collection(tenant_id=tenant_id, region=region)
    return {
        "status": "queued",
        "tenant_id": tenant_id,
        "records_ingested": count,
        "event": event_data,
    }
