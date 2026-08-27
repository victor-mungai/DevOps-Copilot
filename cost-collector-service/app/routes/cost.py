from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.connection import get_db
from ..messaging.events import request_cost_collection
from ..services.cost_collection import (
    get_cost_anomalies,
    get_cost_by_account,
    get_cost_by_region,
    get_cost_by_service,
    get_cost_drilldown,
    get_cost_summary,
    get_cost_trend,
    get_executive_opportunities,
    get_resource_cost_attribution,
    ingest_cost_records,
    reconcile_costs,
)
from ..services.cost_collection import _connected_account_ids
from ..services.cost_explorer import fetch_cost_explorer_resource_costs

router = APIRouter()


def _extract_tenant(x_tenant_id: Optional[str] = Header(None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    if x_tenant_id.lower() in {"all", "all-accounts", "all_accounts"}:
        raise HTTPException(status_code=403, detail="Explicit tenant scope is required")
    return x_tenant_id


@router.get("/cost/summary")
def summary(
    range: str = Query("30d"),
    region: Optional[str] = Query(None),
    basis: str = Query("NET_UNBLENDED"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_summary(db, tenant_id=tenant_id, range_days=days, region=region, basis=basis, start_date=start_date, end_date=end_date)


@router.get("/cost/trend")
def trend(
    range: str = Query("30d"),
    granularity: str = Query("daily"),
    region: Optional[str] = Query(None),
    basis: str = Query("NET_UNBLENDED"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_trend(db, tenant_id=tenant_id, range_days=days, granularity=granularity, region=region, basis=basis, start_date=start_date, end_date=end_date)


@router.get("/cost/services")
def services(
    range: str = Query("30d"),
    region: Optional[str] = Query(None),
    basis: str = Query("NET_UNBLENDED"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_by_service(db, tenant_id=tenant_id, range_days=days, region=region, basis=basis, start_date=start_date, end_date=end_date)


@router.get("/cost/regions")
def regions(
    range: str = Query("30d"),
    basis: str = Query("NET_UNBLENDED"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_by_region(db, tenant_id=tenant_id, range_days=days, basis=basis, start_date=start_date, end_date=end_date)


@router.get("/cost/accounts")
def accounts(
    range: str = Query("30d"),
    basis: str = Query("NET_UNBLENDED"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_by_account(db, tenant_id=tenant_id, range_days=days, basis=basis, start_date=start_date, end_date=end_date)


@router.get("/cost/resource-attribution")
def resource_attribution(
    range: str = Query("14d"),
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 14 if range not in {"7d", "30d"} else (7 if range == "7d" else 14)
    return get_resource_cost_attribution(db, tenant_id=tenant_id, range_days=days, region=region)


@router.get("/cost/resource-attribution/hourly")
def hourly_resource_attribution(
    range: str = Query("7d"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    """Return hourly resource costs only when AWS Cost Explorer provides them.

    This endpoint deliberately does not estimate runtime hours or allocate a
    service total to resources. An empty response is an honest AWS no-data state.
    """
    days = 7 if range != "14d" else 14
    end = date.today()
    start = end - timedelta(days=days)
    items = []
    for account_id in _connected_account_ids(tenant_id):
        items.extend(fetch_cost_explorer_resource_costs(
            tenant_id, account_id, start.isoformat(), end.isoformat(), granularity="HOURLY"
        ))
    return {
        "tenant_id": tenant_id,
        "granularity": "HOURLY",
        "source": "AWS_COST_EXPLORER_GET_COST_AND_USAGE_WITH_RESOURCES",
        "items": items,
        "hours_run": "No data available; AWS Cost Explorer reports attributed cost buckets, not instance runtime state.",
    }


@router.get("/cost/forecast")
def forecast(
    range: str = Query("30d"),
    basis: str = Query("NET_UNBLENDED"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    summary_data = get_cost_summary(db, tenant_id=tenant_id, range_days=30, basis=basis)
    return {
        "tenant_id": tenant_id,
        "calculation_basis": summary_data["calculation_basis"],
        "projected_monthly": summary_data["projected_monthly"],
        "confidence": "no_data" if summary_data["projected_monthly"] == 0 else "derived_from_cost_history",
        "currency": "USD",
    }


@router.get("/cost/anomalies")
def anomalies(
    range: str = Query("30d"),
    basis: str = Query("NET_UNBLENDED"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_anomalies(db, tenant_id=tenant_id, range_days=days, basis=basis)


@router.get("/cost/reconciliation")
def reconciliation(
    basis: str = Query("NET_UNBLENDED"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    return reconcile_costs(db, tenant_id=tenant_id, basis=basis)


@router.get("/cost/drilldown")
def drilldown(
    service: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    range: str = Query("30d"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    days = 90 if range == "90d" else (60 if range == "60d" else 30)
    return get_cost_drilldown(db, tenant_id=tenant_id, service_name=service, region=region, range_days=days, start_date=start_date, end_date=end_date)


@router.get("/cost/opportunities")
def opportunities(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    return get_executive_opportunities(db, tenant_id=tenant_id)


@router.post("/cost/collect")
def trigger_collect(
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_extract_tenant),
):
    count = ingest_cost_records(db, tenant_id=tenant_id, days=90)
    event_data = request_cost_collection(tenant_id=tenant_id, region=region or "")
    return {
        "status": "queued",
        "tenant_id": tenant_id,
        "records_ingested": count,
        "event": event_data,
    }
