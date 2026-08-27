from decimal import Decimal
from typing import Any


def normalize_service_name(raw_name: str) -> str:
    if not raw_name:
        raise ValueError("service name is required from AWS Cost Explorer")
    return raw_name.strip()


def _to_decimal(val: Any) -> Decimal:
    if val is None or val == "":
        return Decimal("0.0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0.0")


def normalize_cost_entry(
    tenant_id: str,
    aws_account_id: str,
    billing_date: str,
    raw_service: str,
    region: str | None,
    usage_type: str | None,
    record_type: str | None = None,
    unblended_cost: Any = 0.0,
    amortized_cost: Any = 0.0,
    net_unblended_cost: Any = 0.0,
    net_amortized_cost: Any = 0.0,
) -> dict[str, Any]:
    if not aws_account_id:
        raise ValueError("aws_account_id is required from AWS Cost Explorer context")

    u_dec = _to_decimal(unblended_cost)
    a_dec = _to_decimal(amortized_cost if amortized_cost is not None else unblended_cost)
    nu_dec = _to_decimal(net_unblended_cost if net_unblended_cost is not None else unblended_cost)
    na_dec = _to_decimal(net_amortized_cost if net_amortized_cost is not None else amortized_cost)

    return {
        "tenant_id": tenant_id,
        "aws_account_id": aws_account_id,
        "billing_date": billing_date,
        "service_name": normalize_service_name(raw_service),
        "region": region.strip() if region else None,
        "usage_type": usage_type,
        "record_type": record_type,
        "unblended_cost": u_dec,
        "amortized_cost": a_dec,
        "net_unblended_cost": nu_dec,
        "net_amortized_cost": na_dec,
        "currency": "USD",
    }
