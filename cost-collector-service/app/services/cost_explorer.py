import os
import logging
import json
from datetime import datetime, timedelta
import requests
from .cost_normalizer import normalize_cost_entry

logger = logging.getLogger("cost-collector")


def fetch_cost_explorer_billing(
    tenant_id: str,
    days: int = 90,
    aws_account_id: str | None = None,
    start_date_str: str | None = None,
    end_date_str: str | None = None,
) -> list[dict]:
    """Fetch daily cost records strictly from AWS Cost Explorer API for connected tenant."""
    records: list[dict] = []
    if start_date_str and end_date_str:
        s_date_req = start_date_str
        # Cost Explorer's end date is exclusive; the API contract uses an inclusive end date.
        e_date_req = (datetime.strptime(end_date_str, "%Y-%m-%d").date() + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        end_date = datetime.utcnow().date() + timedelta(days=1)
        start_date = end_date - timedelta(days=days + 1)
        s_date_req = start_date.strftime("%Y-%m-%d")
        e_date_req = end_date.strftime("%Y-%m-%d")

    connector_url = os.getenv("AWS_CONNECTOR_BASE_URL", "http://127.0.0.1:8003/aws").rstrip("/")

    # Primary attempt: Request all 4 financial metrics (Net and Gross)
    metrics_to_query = ["UnblendedCost", "AmortizedCost", "NetUnblendedCost", "NetAmortizedCost"]
    
    def _do_query(m_list: list[str]):
        request_body = {
            "start_date": s_date_req,
            "end_date": e_date_req,
            "granularity": "DAILY",
            "metrics": m_list,
            "group_by": [
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "REGION"},
            ],
            "account_id": aws_account_id,
        }
        logger.info("COST_EXPLORER_REQUEST tenant=%s account=%s params=%s", tenant_id, aws_account_id, request_body)
        return requests.post(
            f"{connector_url}/{tenant_id}/cost-and-usage",
            json=request_body,
            timeout=30,
        )

    try:
        resp = _do_query(metrics_to_query)
        if resp.status_code != 200:
            # Fallback attempt if Net metrics are unsupported by the AWS account settings
            metrics_to_query = ["UnblendedCost", "AmortizedCost"]
            resp = _do_query(metrics_to_query)
        
        resp.raise_for_status()
        payload = resp.json()
        body = payload.get("data", payload) if isinstance(payload, dict) else {}
        logger.info(
            "COST_EXPLORER_RAW tenant=%s account=%s status=%s response=%s",
            tenant_id, aws_account_id, resp.status_code, json.dumps(body, default=str),
        )
        default_account_id = aws_account_id or body.get("AwsAccountId")
        if not default_account_id:
            raise ValueError("AWS Cost Explorer response did not include an account id")

        for time_period in body.get("ResultsByTime", []):
            b_date = time_period["TimePeriod"]["Start"]
            for group in time_period.get("Groups", []):
                keys = group.get("Keys", [])
                service = keys[0] if len(keys) > 0 and keys[0] else None
                reg = keys[1] if len(keys) > 1 and keys[1] else None
                if not service:
                    logger.warning("Skipping Cost Explorer group with incomplete AWS dimensions: %s", keys)
                    continue
                
                acc_id = default_account_id
                m_dict = group.get("Metrics", {})

                u_val = m_dict.get("UnblendedCost", {}).get("Amount", "0")
                a_val = m_dict.get("AmortizedCost", {}).get("Amount", u_val)
                nu_val = m_dict.get("NetUnblendedCost", {}).get("Amount", u_val)
                na_val = m_dict.get("NetAmortizedCost", {}).get("Amount", a_val)

                # Preserve ALL valid AWS records (including 0, negative refunds/credits, and small decimals)
                records.append(
                    normalize_cost_entry(
                        tenant_id=tenant_id,
                        aws_account_id=acc_id,
                        billing_date=b_date,
                        raw_service=service,
                        region=reg,
                        usage_type=None,
                        record_type=None,
                        unblended_cost=u_val,
                        amortized_cost=a_val,
                        net_unblended_cost=nu_val,
                        net_amortized_cost=na_val,
                    )
                )

        if records:
            logger.info("Successfully fetched %d cost records from AWS Cost Explorer for tenant %s", len(records), tenant_id)
            return records
    except Exception as exc:
        logger.warning("AWS Cost Explorer query for tenant %s failed: %s", tenant_id, exc)

    return records


def fetch_cost_explorer_resource_costs(
    tenant_id: str,
    aws_account_id: str,
    start_date_str: str,
    end_date_str: str,
    granularity: str = "DAILY",
) -> list[dict]:
    """Fetch resource costs only when AWS Cost Explorer explicitly returns them.

    GetCostAndUsageWithResources is limited to recent data and supported AWS
    services. A failure is intentionally represented by no records, never a
    fabricated allocation of a service total.
    """
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    earliest_supported = datetime.utcnow().date() - timedelta(days=14)
    start = max(start, earliest_supported)
    if start > end:
        return []

    connector_url = os.getenv("AWS_CONNECTOR_BASE_URL", "http://127.0.0.1:8003/aws").rstrip("/")
    try:
        response = requests.post(
            f"{connector_url}/{tenant_id}/cost-and-usage/resources",
            json={
                "start_date": start.isoformat(),
                "end_date": (end + timedelta(days=1)).isoformat(),
                "metrics": ["UnblendedCost", "NetUnblendedCost"],
                "account_id": aws_account_id,
                "granularity": granularity,
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json().get("data", {})
    except Exception as exc:  # AWS may not have resource-level CE enabled.
        logger.info("No AWS resource-cost attribution for tenant %s account %s: %s", tenant_id, aws_account_id, exc)
        return []

    records: list[dict] = []
    for period in body.get("ResultsByTime", []):
        billing_date = period.get("TimePeriod", {}).get("Start")
        for group in period.get("Groups", []):
            keys = group.get("Keys", [])
            region = keys[0] if len(keys) > 0 and keys[0] else None
            resource_id = keys[1] if len(keys) > 1 and keys[1] else None
            if not billing_date or not resource_id:
                continue
            metrics = group.get("Metrics", {})
            records.append({
                "tenant_id": tenant_id,
                "aws_account_id": aws_account_id,
                "billing_date": billing_date,
                "billing_timestamp": billing_date if granularity == "HOURLY" else None,
                "service_name": "Amazon Elastic Compute Cloud - Compute",
                "region": region,
                "resource_id": resource_id,
                "unblended_cost": metrics.get("UnblendedCost", {}).get("Amount", "0"),
                "net_unblended_cost": metrics.get("NetUnblendedCost", {}).get("Amount", metrics.get("UnblendedCost", {}).get("Amount", "0")),
                "currency": metrics.get("UnblendedCost", {}).get("Unit", "USD"),
            })
    return records
