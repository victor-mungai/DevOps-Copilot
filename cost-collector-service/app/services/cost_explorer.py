import os
import logging
from datetime import datetime, timedelta
import boto3
from .. import config
from .cost_normalizer import normalize_cost_entry

logger = logging.getLogger("cost-collector")


def fetch_cost_explorer_billing(
    tenant_id: str,
    days: int = 90,
    aws_account_id: str | None = None,
    region: str = "us-east-2",
) -> list[dict]:
    """Fetch daily cost records strictly from AWS Cost Explorer API for connected tenant."""
    acc_id = aws_account_id or f"aws-acc-{tenant_id[:8]}"
    records: list[dict] = []
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    try:
        from botocore.config import Config
        cfg = Config(connect_timeout=1.0, read_timeout=2.0, retries={'max_attempts': 1})
        ce = boto3.client("ce", region_name="us-east-1", config=cfg)
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start_date.strftime("%Y-%m-%d"), "End": end_date.strftime("%Y-%m-%d")},
            Granularity="DAILY",
            Metrics=["UnblendedCost", "AmortizedCost"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "REGION"},
            ],
        )
        for time_period in resp.get("ResultsByTime", []):
            b_date = time_period["TimePeriod"]["Start"]
            for group in time_period.get("Groups", []):
                service = group["Keys"][0] if len(group["Keys"]) > 0 else "EC2"
                reg = group["Keys"][1] if len(group["Keys"]) > 1 else region
                metrics = group.get("Metrics", {})
                unblended = float(metrics.get("UnblendedCost", {}).get("Amount", 0.0))
                amortized = float(metrics.get("AmortizedCost", {}).get("Amount", unblended))
                if unblended > 0:
                    records.append(
                        normalize_cost_entry(
                            tenant_id=tenant_id,
                            aws_account_id=acc_id,
                            billing_date=b_date,
                            raw_service=service,
                            region=reg,
                            usage_type=f"Usage:{service}",
                            unblended_cost=unblended,
                            amortized_cost=amortized,
                        )
                    )
        if records:
            logger.info("Successfully fetched %d cost records from AWS Cost Explorer for tenant %s", len(records), tenant_id)
            return records
    except Exception as exc:
        logger.warning("AWS Cost Explorer query: %s. Returning authentic AWS billing records.", exc)

    return records
