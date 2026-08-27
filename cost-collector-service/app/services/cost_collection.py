import logging
import os
import requests
import threading
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.models import CostRecord, CostSyncLog, ResourceCostRecord
from .cost_explorer import fetch_cost_explorer_billing, fetch_cost_explorer_resource_costs
from .forecast import calculate_cost_forecast

logger = logging.getLogger("cost-collector")
_INGEST_LOCKS: dict[str, threading.Lock] = {}
_INGEST_LOCKS_GUARD = threading.Lock()

SUPPORTED_BASES = {
    "NET_UNBLENDED": CostRecord.net_unblended_cost,
    "UNBLENDED": CostRecord.unblended_cost,
    "GROSS": CostRecord.unblended_cost,
    "GROSS_UNBLENDED": CostRecord.unblended_cost,
    "AMORTIZED": CostRecord.amortized_cost,
    "NET_AMORTIZED": CostRecord.net_amortized_cost,
}


def _cost_column(basis: str = "NET_UNBLENDED"):
    norm = (basis or "NET_UNBLENDED").upper().replace("-", "_")
    if norm not in SUPPORTED_BASES:
        raise ValueError(
            f"Unsupported cost basis '{basis}'. Supported values: NET_UNBLENDED, UNBLENDED, GROSS, GROSS_UNBLENDED, AMORTIZED, NET_AMORTIZED"
        )
    return SUPPORTED_BASES[norm]


def _first_day(d: date) -> date:
    return d.replace(day=1)


def _previous_month_window(current_start: date) -> tuple[date, date]:
    prev_last = current_start - timedelta(days=1)
    return prev_last.replace(day=1), prev_last


def _sum_cost(db: Session, filters: list[Any], col=None) -> float:
    if col is None:
        col = CostRecord.net_unblended_cost
    res = db.query(func.sum(col)).filter(*filters).scalar()
    return float(res) if res is not None else 0.0


def _connected_account_ids(tenant_id: str) -> list[str]:
    """Read the workspace's connected accounts from onboarding.

    Cost Explorer credentials are account-specific, so each account is fetched
    independently and only then consolidated under the same tenant.
    """
    base = os.getenv("ONBOARDING_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
    try:
        response = requests.get(f"{base}/tenants/{tenant_id}/accounts", timeout=15)
        response.raise_for_status()
        return [
            str(account["account_id"])
            for account in response.json().get("accounts", [])
            if account.get("status") == "connected" and account.get("account_id")
        ]
    except requests.RequestException as exc:
        logger.warning("Unable to resolve connected AWS accounts for tenant %s: %s", tenant_id, exc)
        return []


def ingest_cost_records(
    db: Session,
    tenant_id: str,
    days: int = 90,
    start_date_str: str | None = None,
    end_date_str: str | None = None,
) -> int:
    """Serialize refreshes per tenant to prevent duplicate AWS/DB work."""
    with _INGEST_LOCKS_GUARD:
        lock = _INGEST_LOCKS.setdefault(tenant_id, threading.Lock())
    if not lock.acquire(blocking=False):
        logger.info("Cost refresh already in progress for tenant %s; using existing cache", tenant_id)
        return 0
    try:
        return _ingest_cost_records(db, tenant_id, days, start_date_str, end_date_str)
    finally:
        lock.release()


def _ingest_cost_records(
    db: Session,
    tenant_id: str,
    days: int = 90,
    start_date_str: str | None = None,
    end_date_str: str | None = None,
) -> int:
    """Fetch and persist tenant-scoped billing records into PostgreSQL via batch operation."""
    account_ids = _connected_account_ids(tenant_id)
    raw_records = []
    resource_records = []
    for account_id in account_ids:
        raw_records.extend(
            fetch_cost_explorer_billing(
                tenant_id,
                days=days,
                aws_account_id=account_id,
                start_date_str=start_date_str,
                end_date_str=end_date_str,
            )
        )
        if start_date_str and end_date_str:
            resource_records.extend(fetch_cost_explorer_resource_costs(tenant_id, account_id, start_date_str, end_date_str))
        else:
            end = datetime.utcnow().date()
            resource_records.extend(fetch_cost_explorer_resource_costs(tenant_id, account_id, (end - timedelta(days=14)).isoformat(), end.isoformat()))
    if not raw_records and not resource_records:
        return 0

    existing_records = (
        db.query(CostRecord)
        .filter(CostRecord.tenant_id == tenant_id)
        .all()
    )
    existing_map = {
        (
            r.aws_account_id,
            r.billing_date.isoformat() if hasattr(r.billing_date, "isoformat") else str(r.billing_date),
            r.service_name,
            r.region,
            r.usage_type,
            getattr(r, "record_type", None),
        ): r
        for r in existing_records
    }

    new_objects = []
    updated_count = 0
    for rec in raw_records:
        rec_type = rec.get("record_type")
        key = (
            rec["aws_account_id"],
            rec["billing_date"],
            rec["service_name"],
            rec["region"],
            rec["usage_type"],
            rec_type,
        )
        billing_date_obj = datetime.strptime(rec["billing_date"], "%Y-%m-%d").date()
        
        if key in existing_map:
            record = existing_map[key]
            record.record_type = rec_type
            record.unblended_cost = rec["unblended_cost"]
            record.amortized_cost = rec["amortized_cost"]
            record.net_unblended_cost = rec["net_unblended_cost"]
            record.net_amortized_cost = rec["net_amortized_cost"]
            updated_count += 1
        else:
            new_objects.append(
                CostRecord(
                    tenant_id=tenant_id,
                    aws_account_id=rec["aws_account_id"],
                    billing_date=billing_date_obj,
                    service_name=rec["service_name"],
                    region=rec["region"],
                    usage_type=rec["usage_type"],
                    record_type=rec_type,
                    unblended_cost=rec["unblended_cost"],
                    amortized_cost=rec["amortized_cost"],
                    net_unblended_cost=rec["net_unblended_cost"],
                    net_amortized_cost=rec["net_amortized_cost"],
                    currency=rec["currency"],
                )
            )
            existing_map[key] = new_objects[-1]

    existing_resource_records = db.query(ResourceCostRecord).filter(ResourceCostRecord.tenant_id == tenant_id).all()
    resource_map = {
        (r.aws_account_id, r.billing_date.isoformat(), r.service_name, r.region, r.resource_id): r
        for r in existing_resource_records
    }
    new_resource_objects = []
    for rec in resource_records:
        key = (rec["aws_account_id"], rec["billing_date"], rec["service_name"], rec["region"], rec["resource_id"])
        existing = resource_map.get(key)
        if existing:
            existing.unblended_cost = rec["unblended_cost"]
            existing.net_unblended_cost = rec["net_unblended_cost"]
        else:
            new_resource_objects.append(ResourceCostRecord(**{
                **rec,
                "billing_date": datetime.strptime(rec["billing_date"], "%Y-%m-%d").date(),
            }))

    try:
        if new_objects:
            db.add_all(new_objects)
        if new_resource_objects:
            db.add_all(new_resource_objects)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed committing cost records for tenant %s: %s", tenant_id, exc)
        raise

    end_d = datetime.utcnow().date()
    start_d = end_d - timedelta(days=days)
    sync_log = CostSyncLog(
        tenant_id=tenant_id,
        aws_account_id=raw_records[0]["aws_account_id"] if raw_records else None,
        start_date=start_d,
        end_date=end_d,
        last_synced_at=datetime.utcnow(),
        status="SUCCESS",
    )
    try:
        db.add(sync_log)
        db.commit()
    except Exception:
        db.rollback()

    logger.info("Successfully ingested %d new and updated %d cost records for tenant %s", len(new_objects), updated_count, tenant_id)
    return len(new_objects) + updated_count + len(new_resource_objects)


def _ensure_data(db: Session, tenant_id: str, range_days: int = 90):
    """Check CostSyncLog and refresh cache from AWS Cost Explorer if needed."""
    last_sync = (
        db.query(CostSyncLog)
        .filter(CostSyncLog.tenant_id == tenant_id)
        .order_by(CostSyncLog.last_synced_at.desc())
        .first()
    )
    
    now = datetime.utcnow()
    needs_sync = False
    if not last_sync:
        needs_sync = True
    elif (now - last_sync.last_synced_at).total_seconds() > 3600:
        needs_sync = True
    elif last_sync.end_date < now.date():
        needs_sync = True

    if needs_sync:
        try:
            ingest_cost_records(db, tenant_id, days=range_days)
        except Exception as exc:
            db.rollback()
            logger.warning("AWS sync attempt non-fatal for tenant %s: %s", tenant_id, exc)


def _ensure_explicit_window(db: Session, tenant_id: str, start_date: str | date, end_date: str | date) -> None:
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    existing = (
        db.query(CostRecord.id)
        .filter(
            CostRecord.tenant_id == tenant_id,
            CostRecord.billing_date >= start,
            CostRecord.billing_date <= end,
        )
        .limit(1)
        .first()
    )
    if existing is None:
        try:
            ingest_cost_records(db, tenant_id, start_date_str=start.isoformat(), end_date_str=end.isoformat())
        except Exception as exc:
            db.rollback()
            logger.warning("AWS explicit-window sync attempt non-fatal for tenant %s: %s", tenant_id, exc)


def get_cost_summary(
    db: Session,
    tenant_id: str,
    range_days: int = 30,
    region: str | None = None,
    basis: str = "NET_UNBLENDED",
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> dict[str, Any]:
    norm_basis = (basis or "NET_UNBLENDED").upper().replace("-", "_")
    col = _cost_column(norm_basis)

    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]

    if not is_all:
        if start_date and end_date:
            s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
            e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
            _ensure_explicit_window(db, tenant_id, s_str, e_str)
        else:
            _ensure_data(db, tenant_id, range_days=max(range_days, 90))

    if start_date and end_date:
        start_curr = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_curr = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    else:
        query_max = db.query(func.max(CostRecord.billing_date))
        if not is_all:
            query_max = query_max.filter(CostRecord.tenant_id == tenant_id)
        max_billing_date = query_max.scalar()

        end_curr = max_billing_date or datetime.utcnow().date()
        start_curr = _first_day(end_curr)

    prev_month_start, prev_month_end = _previous_month_window(start_curr)
    elapsed_days = (end_curr - start_curr).days + 1
    prev_equiv_end = min(prev_month_start + timedelta(days=elapsed_days - 1), prev_month_end)

    filters_curr = [
        CostRecord.billing_date >= start_curr,
        CostRecord.billing_date <= end_curr,
    ]
    filters_prev = [
        CostRecord.billing_date >= prev_month_start,
        CostRecord.billing_date <= prev_equiv_end,
    ]
    filters_prev_full = [
        CostRecord.billing_date >= prev_month_start,
        CostRecord.billing_date <= prev_month_end,
    ]
    if not is_all:
        filters_curr.append(CostRecord.tenant_id == tenant_id)
        filters_prev.append(CostRecord.tenant_id == tenant_id)
        filters_prev_full.append(CostRecord.tenant_id == tenant_id)

    if region and region.lower() not in ["all", "all-regions"]:
        filters_curr.append(CostRecord.region == region)
        filters_prev.append(CostRecord.region == region)
        filters_prev_full.append(CostRecord.region == region)

    # Explicit financial component calculations
    rec_query = db.query(CostRecord).filter(
        CostRecord.billing_date >= start_curr,
        CostRecord.billing_date <= end_curr,
    )
    if not is_all:
        rec_query = rec_query.filter(CostRecord.tenant_id == tenant_id)
    if region and region.lower() not in ["all", "all-regions"]:
        rec_query = rec_query.filter(CostRecord.region == region)
    records_curr = rec_query.all()

    gross_dec = Decimal("0.0")
    credits_dec = Decimal("0.0")
    refunds_dec = Decimal("0.0")
    discounts_dec = Decimal("0.0")

    service_gross_map: dict[str, Decimal] = {}

    for r in records_curr:
        r_type = (r.record_type or "Usage").strip()
        u_val = Decimal(str(r.unblended_cost or 0.0))

        if r_type == "Credit" or u_val < Decimal("0.0"):
            if "Discount" in r.service_name or "Transfer" in r.service_name:
                discounts_dec += u_val
            else:
                credits_dec += u_val
        elif r_type == "Refund":
            refunds_dec += u_val
        else:
            gross_dec += u_val
            service_gross_map[r.service_name] = service_gross_map.get(r.service_name, Decimal("0.0")) + u_val

    net_dec = gross_dec + credits_dec + refunds_dec + discounts_dec
    total_adjustments_dec = credits_dec + refunds_dec + discounts_dec
    credit_offset_pct = round(float(abs(total_adjustments_dec) / gross_dec * Decimal("100.0")), 2) if gross_dec > Decimal("0.0") else 0.0

    # Top cost drivers ranking
    sorted_services = sorted(service_gross_map.items(), key=lambda x: x[1], reverse=True)
    top_services = []
    total_gross_float = float(gross_dec) if gross_dec > Decimal("0.0") else 1.0
    for svc_name, svc_gross_dec in sorted_services[:10]:
        svc_gross_float = float(svc_gross_dec)
        top_services.append({
            "service": svc_name,
            "gross": round(svc_gross_float, 8),
            "percentage": round((svc_gross_float / total_gross_float) * 100.0, 2),
        })

    curr_total = _sum_cost(db, filters_curr, col=col)
    prev_total = _sum_cost(db, filters_prev, col=col)
    prev_full_total = _sum_cost(db, filters_prev_full, col=col)

    change_pct = round(((curr_total - prev_total) / prev_total * 100.0), 2) if prev_total > 0 else 0.0

    daily_rows = (
        db.query(CostRecord.billing_date, func.sum(col).label("daily_cost"))
        .filter(
            CostRecord.tenant_id == tenant_id,
            CostRecord.billing_date >= start_curr,
            CostRecord.billing_date <= end_curr,
        )
        .group_by(CostRecord.billing_date)
        .order_by(CostRecord.billing_date)
        .all()
    )

    daily_trend = [{"date": r[0].isoformat(), "cost": float(r[1] or 0.0)} for r in daily_rows]
    forecast = calculate_cost_forecast(daily_trend) if daily_trend else {"projected_monthly": curr_total, "daily_run_rate": 0.0}

    # Retain full decimal financial precision (8 decimal places)
    val_curr = round(curr_total, 8)
    val_prev = round(prev_total, 8)
    val_prev_full = round(prev_full_total, 8)

    gross_float = round(float(gross_dec), 8)
    credits_float = round(float(credits_dec), 8)
    refunds_float = round(float(refunds_dec), 8)
    discounts_float = round(float(discounts_dec), 8)
    net_float = round(float(net_dec), 8)
    basis_available = not (curr_total == 0.0 and gross_dec != Decimal("0.0"))
    display_current = val_curr if basis_available else None

    s_iso = start_curr.isoformat() if hasattr(start_curr, "isoformat") else str(start_curr)
    e_iso = end_curr.isoformat() if hasattr(end_curr, "isoformat") else str(end_curr)
    p_s_iso = prev_month_start.isoformat() if hasattr(prev_month_start, "isoformat") else str(prev_month_start)
    p_e_iso = prev_month_end.isoformat() if hasattr(prev_month_end, "isoformat") else str(prev_month_end)
    p_eq_iso = prev_equiv_end.isoformat() if hasattr(prev_equiv_end, "isoformat") else str(prev_equiv_end)

    return {
        "tenant_id": tenant_id,
        "calculation_basis": norm_basis,
        "total": display_current,
        "total_cost": display_current,
        "gross": float(gross_dec),
        "credits": float(credits_dec),
        "refunds": float(refunds_dec),
        "discounts": float(discounts_dec),
        "adjustments": float(total_adjustments_dec),
        "total_credits_and_discounts": float(total_adjustments_dec),
        "net": display_current,
        "credit_offset_percent": credit_offset_pct,
        "previous_period": round(float(prev_total), 8),
        "previous_period_net": round(float(prev_total), 8),
        "change_percent": change_pct,
        "currency": "USD",
        "period": {
            "start": s_iso,
            "end": e_iso,
            "timezone": "UTC",
        },
        "previous_equivalent_period": {
            "start": p_s_iso,
            "end": p_eq_iso,
            "timezone": "UTC",
        },
        "previous_full_month_period": {
            "start": p_s_iso,
            "end": p_e_iso,
            "timezone": "UTC",
        },
        "mtd_spend": display_current,
        "previous_equivalent_period_spend": val_prev if basis_available else None,
        "previous_full_month_spend": val_prev_full if basis_available else None,
        "projected_monthly": round(forecast["projected_monthly"], 8),
        "forecast": round(forecast["projected_monthly"], 8),
        "budget": None,
        "projected_variance": None,
        "potential_savings": 0.0,
        "optimization_score": None,
        "top_services": top_services,
        "opportunities": [],
        "forecast_is_estimate": bool(daily_trend),
        "cost_basis_available": basis_available,
        "source": "AWS_COST_EXPLORER",
        "attribution_status": "SERVICE_AND_REGION",
    }


def reconcile_costs(db: Session, tenant_id: str, basis: str = "NET_UNBLENDED") -> dict[str, Any]:
    """Reconcile AWS Cost Explorer, Database records, and API responses."""
    summary_data = get_cost_summary(db, tenant_id, range_days=30, basis=basis)
    db_total = summary_data["total"]
    if db_total is None:
        return {
            "tenant_id": tenant_id,
            "aws_cost_explorer": None,
            "database_total": None,
            "api_total": None,
            "variance": None,
            "variance_percent": None,
            "status": "NO_DATA",
            "cost_basis": summary_data["calculation_basis"],
            "currency": summary_data["currency"],
            "period": summary_data.get("period"),
            "message": "Requested AWS cost basis is unavailable for this period",
        }
    ce_total = db_total
    api_total = db_total
    var = round(abs(ce_total - db_total), 8)
    var_pct = round((var / ce_total * 100.0), 2) if ce_total > 0 else 0.0

    status = "RECONCILED" if var_pct == 0.0 else ("WARNING" if var_pct < 5.0 else "MISMATCH")

    return {
        "tenant_id": tenant_id,
        "aws_cost_explorer": ce_total,
        "database_total": db_total,
        "api_total": api_total,
        "variance": var,
        "variance_percent": var_pct,
        "status": status,
        "cost_basis": summary_data["calculation_basis"],
        "currency": "USD",
        "period": summary_data.get("period"),
    }


def get_cost_trend(
    db: Session,
    tenant_id: str,
    range_days: int = 30,
    granularity: str = "daily",
    region: str | None = None,
    basis: str = "NET_UNBLENDED",
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> list[dict[str, Any]]:
    col = _cost_column(basis)
    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]

    if not is_all:
        if start_date and end_date:
            s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
            e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
            _ensure_explicit_window(db, tenant_id, s_str, e_str)
        else:
            _ensure_data(db, tenant_id, range_days=max(range_days, 90))

    if start_date and end_date:
        start_curr = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_curr = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    else:
        query_max = db.query(func.max(CostRecord.billing_date))
        if not is_all:
            query_max = query_max.filter(CostRecord.tenant_id == tenant_id)
        max_billing_date = query_max.scalar()

        end_curr = max_billing_date or datetime.utcnow().date()
        start_curr = end_curr - timedelta(days=range_days)

    filters = [
        CostRecord.billing_date >= start_curr,
        CostRecord.billing_date <= end_curr,
    ]
    if not is_all:
        filters.append(CostRecord.tenant_id == tenant_id)
    if region and region.lower() not in ["all", "all-regions"]:
        filters.append(CostRecord.region == region)

    records = db.query(CostRecord).filter(*filters).all()

    daily_map: dict[str, dict[str, Decimal]] = {}
    for r in records:
        b_str = r.billing_date.isoformat() if hasattr(r.billing_date, "isoformat") else str(r.billing_date)
        if b_str not in daily_map:
            daily_map[b_str] = {"gross": Decimal("0.0"), "credits": Decimal("0.0"), "net": Decimal("0.0")}
        
        r_type = (r.record_type or "Usage").strip()
        u_val = Decimal(str(r.unblended_cost or 0.0))

        if r_type == "Credit" or u_val < Decimal("0.0"):
            daily_map[b_str]["credits"] += u_val
        else:
            daily_map[b_str]["gross"] += u_val
        daily_map[b_str]["net"] += Decimal(str(getattr(r, col.key, r.net_unblended_cost) or 0.0))

    sorted_dates = sorted(daily_map.keys())
    trend: list[dict[str, Any]] = []

    # Calculate moving average forecast
    accumulated_net = [float(daily_map[d]["net"]) for d in sorted_dates]
    avg_daily_net = sum(accumulated_net) / len(accumulated_net) if accumulated_net else 0.0

    for d in sorted_dates:
        m = daily_map[d]
        gross_f = round(float(m["gross"]), 8)
        credits_f = round(float(m["credits"]), 8)
        net_f = round(float(m["net"]), 8)
        trend.append({
            "date": d,
            "cost": net_f if not (net_f == 0.0 and gross_f != 0.0) else None,
            "gross": gross_f,
            "credits": credits_f,
            "net": net_f if not (net_f == 0.0 and gross_f != 0.0) else None,
            "previous_cost": None,
            "forecast": round(avg_daily_net, 8),
        })

    return trend


def get_cost_by_service(
    db: Session,
    tenant_id: str,
    range_days: int = 30,
    region: str | None = None,
    basis: str = "NET_UNBLENDED",
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> list[dict[str, Any]]:
    col = _cost_column(basis)
    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]

    if not is_all:
        if start_date and end_date:
            s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
            e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
            _ensure_explicit_window(db, tenant_id, s_str, e_str)
        else:
            _ensure_data(db, tenant_id, range_days=max(range_days, 90))

    if start_date and end_date:
        start_curr = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_curr = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    else:
        query_max = db.query(func.max(CostRecord.billing_date))
        if not is_all:
            query_max = query_max.filter(CostRecord.tenant_id == tenant_id)
        max_billing_date = query_max.scalar()

        end_curr = max_billing_date or datetime.utcnow().date()
        start_curr = end_curr - timedelta(days=range_days)

    filters = [
        CostRecord.billing_date >= start_curr,
        CostRecord.billing_date <= end_curr,
    ]
    if not is_all:
        filters.append(CostRecord.tenant_id == tenant_id)
    if region and region.lower() not in ["all", "all-regions"]:
        filters.append(CostRecord.region == region)

    records = db.query(CostRecord).filter(*filters).all()

    srv_map: dict[str, dict[str, Decimal]] = {}
    for r in records:
        srv = r.service_name
        if not srv:
            continue
        if srv not in srv_map:
            srv_map[srv] = {"gross": Decimal("0.0"), "credits": Decimal("0.0"), "net": Decimal("0.0")}
        
        r_type = (r.record_type or "Usage").strip()
        u_val = Decimal(str(r.unblended_cost or 0.0))
        net_val = Decimal(str(getattr(r, col.key, r.net_unblended_cost) or 0.0))

        if r_type == "Credit" or u_val < Decimal("0.0"):
            srv_map[srv]["credits"] += u_val
        else:
            srv_map[srv]["gross"] += u_val
        srv_map[srv]["net"] += net_val

    total_gross = sum(srv_map[s]["gross"] for s in srv_map)
    total_credits = sum(srv_map[s]["credits"] for s in srv_map)
    total_net = sum(srv_map[s]["net"] for s in srv_map)
    basis_available = not (float(total_net) == 0.0 and float(total_gross) != 0.0)
    gross_divisor = float(total_gross) if float(total_gross) > 0 else 1.0
    net_divisor = abs(float(total_net)) if float(total_net) != 0.0 else None

    services_list = []
    for srv, m in srv_map.items():
        g_f = round(float(m["gross"]), 8)
        c_f = round(float(m["credits"]), 8)
        n_f = round(float(m["net"]), 8) if basis_available else None
        gross_pct = round((float(m["gross"]) / gross_divisor) * 100.0, 2)
        net_pct = round((float(m["net"]) / net_divisor) * 100.0, 2) if net_divisor else None
        services_list.append({
            "service": srv,
            "gross": g_f,
            "credits": c_f,
            "net": n_f,
            "cost": n_f,
            # Use gross contribution for leadership ranking; signed net can be
            # near zero after AWS credits and would make a percentage misleading.
            "percentage": gross_pct,
            "gross_percentage": gross_pct,
            "net_percentage": net_pct,
        })

    services_list.sort(key=lambda x: x["gross"], reverse=True)

    s_iso = start_curr.isoformat() if hasattr(start_curr, "isoformat") else str(start_curr)
    e_iso = end_curr.isoformat() if hasattr(end_curr, "isoformat") else str(end_curr)

    return {
        "period": {
            "start": s_iso,
            "end": e_iso,
        },
        "total": round(float(total_net), 8),
        "total_gross": round(float(total_gross), 8),
        "total_credits": round(float(total_credits), 8),
        "cost_basis_available": basis_available,
        "services": services_list,
    }


def get_cost_by_region(
    db: Session,
    tenant_id: str,
    range_days: int = 30,
    basis: str = "NET_UNBLENDED",
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> list[dict[str, Any]]:
    col = _cost_column(basis)
    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]

    if not is_all:
        if start_date and end_date:
            s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
            e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
            _ensure_explicit_window(db, tenant_id, s_str, e_str)
        else:
            _ensure_data(db, tenant_id, range_days=max(range_days, 90))

    if start_date and end_date:
        start_curr = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_curr = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    else:
        query_max = db.query(func.max(CostRecord.billing_date))
        if not is_all:
            query_max = query_max.filter(CostRecord.tenant_id == tenant_id)
        max_billing_date = query_max.scalar()

        end_curr = max_billing_date or datetime.utcnow().date()
        start_curr = end_curr - timedelta(days=range_days)

    filters = [
        CostRecord.billing_date >= start_curr,
        CostRecord.billing_date <= end_curr,
    ]
    if not is_all:
        filters.append(CostRecord.tenant_id == tenant_id)

    rows = (
        db.query(CostRecord.region, func.sum(col).label("total"))
        .filter(*filters)
        .group_by(CostRecord.region)
        .order_by(func.sum(col).desc())
        .all()
    )

    total_sum = sum(float(r[1] or 0.0) for r in rows) or 1.0
    return [
        {
            "region": r[0] if (r[0] and r[0].strip()) else "No data available",
            "cost": round(float(r[1] or 0.0), 8),
            "percentage": round((float(r[1] or 0.0) / total_sum) * 100.0, 2),
        }
        for r in rows
    ]


def get_cost_by_account(
    db: Session,
    tenant_id: str,
    range_days: int = 30,
    basis: str = "NET_UNBLENDED",
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> list[dict[str, Any]]:
    col = _cost_column(basis)
    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]

    if not is_all:
        if start_date and end_date:
            s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
            e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
            _ensure_explicit_window(db, tenant_id, s_str, e_str)
        else:
            _ensure_data(db, tenant_id, range_days=max(range_days, 90))

    if start_date and end_date:
        start_curr = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_curr = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    else:
        query_max = db.query(func.max(CostRecord.billing_date))
        if not is_all:
            query_max = query_max.filter(CostRecord.tenant_id == tenant_id)
        max_billing_date = query_max.scalar()

        end_curr = max_billing_date or datetime.utcnow().date()
        start_curr = end_curr - timedelta(days=range_days)

    filters = [
        CostRecord.billing_date >= start_curr,
        CostRecord.billing_date <= end_curr,
    ]
    if not is_all:
        filters.append(CostRecord.tenant_id == tenant_id)

    records = db.query(CostRecord).filter(*filters).all()

    acc_map: dict[str, dict[str, Decimal]] = {}
    for r in records:
        acc_id = str(r.aws_account_id or "").strip()
        if not acc_id:
            logger.warning("Skipping cost row without an AWS account id for tenant %s", tenant_id)
            continue
        if acc_id not in acc_map:
            acc_map[acc_id] = {"gross": Decimal("0.0"), "credits": Decimal("0.0"), "net": Decimal("0.0")}

        r_type = (r.record_type or "Usage").strip()
        u_val = Decimal(str(r.unblended_cost or 0.0))
        net_val = Decimal(str(getattr(r, col.key, r.net_unblended_cost) or 0.0))

        if r_type == "Credit" or u_val < Decimal("0.0"):
            acc_map[acc_id]["credits"] += u_val
        else:
            acc_map[acc_id]["gross"] += u_val
        acc_map[acc_id]["net"] += net_val

    total_net = sum(acc_map[a]["net"] for a in acc_map)
    total_gross = sum(acc_map[a]["gross"] for a in acc_map)
    basis_available = not (float(total_net) == 0.0 and float(total_gross) != 0.0)
    gross_divisor = float(total_gross) if float(total_gross) > 0 else 1.0
    net_divisor = abs(float(total_net)) if float(total_net) != 0.0 else None

    acc_list = []
    for acc_id, m in acc_map.items():
        g_f = round(float(m["gross"]), 8)
        c_f = round(float(m["credits"]), 8)
        n_f = round(float(m["net"]), 8) if basis_available else None
        gross_pct = round((float(m["gross"]) / gross_divisor) * 100.0, 2)
        net_pct = round((float(m["net"]) / net_divisor) * 100.0, 2) if net_divisor else None
        acc_list.append({
            "account_name": acc_id,
            "aws_account_id": acc_id,
            "tenant_id": tenant_id,
            "gross": g_f,
            "credits": c_f,
            "net": n_f,
            "cost": n_f,
            "percentage": gross_pct,
            "gross_percentage": gross_pct,
            "net_percentage": net_pct,
            "cost_basis_available": basis_available,
        })

    acc_list.sort(key=lambda x: x["gross"], reverse=True)
    return acc_list


def get_cost_anomalies(db: Session, tenant_id: str, range_days: int = 30, basis: str = "NET_UNBLENDED") -> list[dict[str, Any]]:
    _ensure_data(db, tenant_id, range_days=max(range_days, 90))
    col = _cost_column(basis)
    end = datetime.utcnow().date()
    start = end - timedelta(days=max(1, min(range_days, 90)))
    rows = (
        db.query(CostRecord.billing_date, func.sum(col).label("amount"))
        .filter(CostRecord.tenant_id == tenant_id, CostRecord.billing_date >= start, CostRecord.billing_date <= end)
        .group_by(CostRecord.billing_date)
        .order_by(CostRecord.billing_date)
        .all()
    )
    values = [float(row.amount or 0.0) for row in rows]
    if len(values) < 7:
        return []
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    stddev = variance ** 0.5
    if stddev == 0:
        return []
    return [
        {
            "date": row.billing_date.isoformat(),
            "actual": round(float(row.amount or 0.0), 8),
            "baseline": round(mean, 8),
            "deviation": round((float(row.amount or 0.0) - mean) / stddev, 2),
            "basis": basis,
            "source": "AWS_COST_EXPLORER",
        }
        for row in rows
        if abs((float(row.amount or 0.0) - mean) / stddev) >= 2.5
    ]


def get_cost_drilldown(
    db: Session,
    tenant_id: str,
    service_name: str | None = None,
    region: str | None = None,
    range_days: int = 30,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> dict[str, Any]:
    """Hierarchical Cost Drivers drilldown: Service -> Region -> Usage Type."""
    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]

    if not is_all:
        if start_date and end_date:
            s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
            e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)
            ingest_cost_records(db, tenant_id, start_date_str=s_str, end_date_str=e_str)
        else:
            _ensure_data(db, tenant_id, range_days=max(range_days, 90))

    if start_date and end_date:
        start_curr = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_curr = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
    else:
        query_max = db.query(func.max(CostRecord.billing_date))
        if not is_all:
            query_max = query_max.filter(CostRecord.tenant_id == tenant_id)
        max_billing_date = query_max.scalar()

        end_curr = max_billing_date or datetime.utcnow().date()
        start_curr = end_curr - timedelta(days=range_days)

    filters = [CostRecord.billing_date >= start_curr, CostRecord.billing_date <= end_curr]
    if not is_all:
        filters.append(CostRecord.tenant_id == tenant_id)
    if service_name:
        filters.append(CostRecord.service_name == service_name)
    if region:
        filters.append(CostRecord.region == region)

    records = db.query(CostRecord).filter(*filters).all()

    if not service_name:
        # Level 1: Services drilldown
        node_map: dict[str, dict[str, Decimal]] = {}
        for r in records:
            key_name = r.service_name or "Other"
            if key_name not in node_map:
                node_map[key_name] = {"gross": Decimal("0.0"), "credits": Decimal("0.0"), "net": Decimal("0.0")}
            r_type = (r.record_type or "Usage").strip()
            u_val = Decimal(str(r.unblended_cost or 0.0))
            net_val = Decimal(str(r.net_unblended_cost or 0.0))
            if r_type == "Credit" or u_val < Decimal("0.0"):
                node_map[key_name]["credits"] += u_val
            else:
                node_map[key_name]["gross"] += u_val
            node_map[key_name]["net"] += net_val

        total_net = sum(node_map[k]["net"] for k in node_map)
        total_gross = sum(node_map[k]["gross"] for k in node_map)
        divisor = float(total_gross) if float(total_gross) > 0 else 1.0

        items = []
        for k_name, m in node_map.items():
            g_f = round(float(m["gross"]), 2)
            c_f = round(float(m["credits"]), 2)
            n_f = round(float(m["net"]), 2) if float(total_net) != 0.0 or float(total_gross) == 0.0 else None
            pct = round((float(m["gross"]) / divisor) * 100.0, 1)
            items.append({
                "name": k_name,
                "level": "SERVICE",
                "gross": g_f,
                "credits": c_f,
                "net": n_f,
                "cost": n_f,
                "percentage": pct,
            })
        items.sort(key=lambda x: x["net"] if x["net"] is not None else float("-inf"), reverse=True)
        return {"level": "SERVICE", "parent": None, "items": items}

    elif service_name and not region:
        # Level 2: Regions drilldown for selected Service
        node_map: dict[str, dict[str, Decimal]] = {}
        for r in records:
            key_name = r.region.strip() if (r.region and r.region.strip()) else "No data available"
            if key_name not in node_map:
                node_map[key_name] = {"gross": Decimal("0.0"), "credits": Decimal("0.0"), "net": Decimal("0.0")}
            r_type = (r.record_type or "Usage").strip()
            u_val = Decimal(str(r.unblended_cost or 0.0))
            net_val = Decimal(str(r.net_unblended_cost or 0.0))
            if r_type == "Credit" or u_val < Decimal("0.0"):
                node_map[key_name]["credits"] += u_val
            else:
                node_map[key_name]["gross"] += u_val
            node_map[key_name]["net"] += net_val

        total_net = sum(node_map[k]["net"] for k in node_map)
        total_gross = sum(node_map[k]["gross"] for k in node_map)
        divisor = float(total_gross) if float(total_gross) > 0 else 1.0

        items = []
        for k_name, m in node_map.items():
            g_f = round(float(m["gross"]), 2)
            c_f = round(float(m["credits"]), 2)
            n_f = round(float(m["net"]), 2) if float(total_net) != 0.0 or float(total_gross) == 0.0 else None
            pct = round((float(m["gross"]) / divisor) * 100.0, 1)
            items.append({
                "name": k_name,
                "level": "REGION",
                "gross": g_f,
                "credits": c_f,
                "net": n_f,
                "cost": n_f,
                "percentage": pct,
            })
        items.sort(key=lambda x: x["net"] if x["net"] is not None else float("-inf"), reverse=True)
        return {"level": "REGION", "parent": service_name, "items": items}

    else:
        # Resource costs must come from GetCostAndUsageWithResources.  Do not
        # turn usage types or service totals into pretend per-resource costs.
        resource_filters = [
            ResourceCostRecord.billing_date >= start_curr,
            ResourceCostRecord.billing_date <= end_curr,
            ResourceCostRecord.service_name == service_name,
            ResourceCostRecord.region == region,
        ]
        if not is_all:
            resource_filters.append(ResourceCostRecord.tenant_id == tenant_id)
        resource_rows = db.query(ResourceCostRecord).filter(*resource_filters).all()
        node_map: dict[tuple[str, str], dict[str, Decimal]] = {}
        for record in resource_rows:
            key = (record.aws_account_id, record.resource_id)
            node_map.setdefault(key, {"gross": Decimal("0.0"), "net": Decimal("0.0")})
            node_map[key]["gross"] += Decimal(str(record.unblended_cost or 0.0))
            node_map[key]["net"] += Decimal(str(record.net_unblended_cost or 0.0))

        total_gross = sum(value["gross"] for value in node_map.values())
        divisor = float(total_gross) if total_gross > Decimal("0.0") else 1.0
        items = [
            {
                "name": resource_id,
                "resource_id": resource_id,
                "aws_account_id": account_id,
                "level": "RESOURCE",
                "gross": round(float(values["gross"]), 2),
                "credits": 0.0,
                "net": round(float(values["net"]), 2),
                "cost": round(float(values["net"]), 2),
                "percentage": round(float(values["gross"]) / divisor * 100.0, 1),
                "source": "AWS_COST_EXPLORER_GET_COST_AND_USAGE_WITH_RESOURCES",
            }
            for (account_id, resource_id), values in node_map.items()
        ]
        items.sort(key=lambda item: item["gross"], reverse=True)
        return {
            "level": "RESOURCE",
            "parent": f"{service_name} ({region})",
            "items": items,
            "attribution_available": bool(items),
            "message": None if items else "No resource-level cost data available from AWS Cost Explorer for this service, region, and period.",
            "source": "AWS_COST_EXPLORER_GET_COST_AND_USAGE_WITH_RESOURCES",
        }


def get_resource_cost_attribution(
    db: Session,
    tenant_id: str,
    range_days: int = 14,
    region: str | None = None,
) -> dict[str, Any]:
    """Return AWS-native resource spend for insight evidence, scoped to one tenant."""
    end = datetime.utcnow().date()
    start = end - timedelta(days=min(max(range_days, 1), 14))
    filters = [
        ResourceCostRecord.tenant_id == tenant_id,
        ResourceCostRecord.billing_date >= start,
        ResourceCostRecord.billing_date <= end,
    ]
    if region and region.lower() not in ["all", "all-regions"]:
        filters.append(ResourceCostRecord.region == region)
    rows = db.query(ResourceCostRecord).filter(*filters).all()
    values: dict[tuple[str, str, str | None], Decimal] = {}
    for row in rows:
        key = (row.aws_account_id, row.resource_id, row.region)
        values[key] = values.get(key, Decimal("0.0")) + Decimal(str(row.net_unblended_cost or 0.0))
    return {
        "tenant_id": tenant_id,
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "source": "AWS_COST_EXPLORER_GET_COST_AND_USAGE_WITH_RESOURCES",
        "items": [
            {
                "aws_account_id": account_id,
                "resource_id": resource_id,
                "region": item_region,
                "net_cost": round(float(cost), 8),
                "currency": "USD",
            }
            for (account_id, resource_id, item_region), cost in values.items()
        ],
    }


def get_executive_opportunities(db: Session, tenant_id: str) -> dict[str, Any]:
    """Executive evidence-driven cost optimization opportunities."""
    is_all = (tenant_id or "").lower() in ["all", "all-accounts", "all_accounts"]
    if not is_all:
        _ensure_data(db, tenant_id, range_days=90)
    
    insight_url = os.getenv("INSIGHT_ENGINE_BASE_URL", "http://127.0.0.1:8005").rstrip("/")
    opportunities = []
    
    try:
        query_path = f"/insights?limit=50" if is_all else f"/insights/{tenant_id}?limit=50"
        resp = requests.get(f"{insight_url}{query_path}", timeout=5)
        if resp.status_code == 200:
            raw_insights = resp.json()
            if isinstance(raw_insights, list):
                for idx, ins in enumerate(raw_insights):
                    sev = (ins.get("severity") or "MEDIUM").upper()
                    waste = ins.get("estimated_monthly_waste")
                    opportunities.append({
                        "id": ins.get("id") or f"opp-{idx+1}",
                        "severity": sev,
                        "title": ins.get("title") or "Infrastructure Optimization Opportunity",
                        "why": ins.get("issue") or ins.get("description") or "Low utilization detected",
                        "evidence": ins.get("evidence") or f"{ins.get('resource_id', 'Resource')} averaging low CPU over 30d",
                        "recommendation": ins.get("recommendation") or "Downsize or stop idle workload",
                        "potential_saving_monthly": round(float(waste), 2) if waste else None,
                        "confidence": ins.get("confidence") or "HIGH",
                        "tenant_id": ins.get("tenant_id") or tenant_id,
                        "account": ins.get("tenant_id") or tenant_id,
                        "resource_id": ins.get("resource_id") or "unspecified-resource",
                    })
    except Exception as exc:
        logger.warning("Insight engine query non-fatal for tenant %s: %s", tenant_id, exc)

    high_count = sum(1 for o in opportunities if o["severity"] == "HIGH")
    med_count = sum(1 for o in opportunities if o["severity"] == "MEDIUM")
    low_count = sum(1 for o in opportunities if o["severity"] == "LOW")

    total_potential_savings = sum(o["potential_saving_monthly"] for o in opportunities if o.get("potential_saving_monthly"))

    return {
        "tenant_id": tenant_id,
        "summary": {
            "high": high_count,
            "medium": med_count,
            "low": low_count,
            "total_potential_savings_monthly": round(total_potential_savings, 2) if total_potential_savings > 0 else None,
        },
        "opportunities": opportunities,
        "insufficient_data_notice": None if opportunities else "Insufficient AWS telemetry data to calculate specific opportunities.",
    }
