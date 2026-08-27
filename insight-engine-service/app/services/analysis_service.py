import logging
import os

import httpx

from sqlalchemy.orm import Session

from .. import config
from ..db import insight_repository
from ..rules.base import AnalysisContext, Ec2Signal
from ..rules.registry import get_rules
from ..sources.provider import get_provider
from . import rag_service

logger = logging.getLogger("insight-engine")


def _resource_costs(tenant_id: str, region: str | None) -> dict[tuple[str | None, str, str | None], float]:
    """Read AWS-native resource attribution once for this tenant analysis."""
    base_url = os.getenv("COST_SERVICE_URL", "http://127.0.0.1:8006").rstrip("/")
    try:
        response = httpx.get(
            f"{base_url}/cost/resource-attribution?range=14d",
            headers={"X-Tenant-ID": tenant_id},
            timeout=3.0,
        )
        response.raise_for_status()
        return {
            (item.get("aws_account_id"), item["resource_id"], item.get("region")): float(item.get("net_cost") or 0.0)
            for item in response.json().get("items", [])
            if item.get("resource_id")
        }
    except Exception as exc:  # Attribution is optional AWS data, never inferred.
        logger.info("Resource-cost attribution unavailable for tenant %s: %s", tenant_id, exc)
        return {}


def _build_context(provider, tenant_id: str, region: str | None) -> AnalysisContext:
    """Gather per-tenant signals once, shared across every rule pack."""
    instances = provider.list_ec2_instances(tenant_id, region=region)
    rds_dbs = getattr(provider, "list_rds_databases", lambda t, region=None: [])(tenant_id, region=region) or []
    lambda_fns = getattr(provider, "list_lambda_functions", lambda t, region=None: [])(tenant_id, region=region) or []
    ebs_vols = []
    resource_costs = _resource_costs(tenant_id, region)

    ec2: list[Ec2Signal] = []
    for inst in instances:
        instance_id = inst["instance_id"]
        agg = provider.avg_cpu_over_window(tenant_id, instance_id, config.IDLE_WINDOW_DAYS)
        ec2.append(
            Ec2Signal(
                resource_id=instance_id,
                instance_type=inst.get("instance_type"),
                avg_cpu=agg["avg"] if agg else None,
                samples=agg["samples"] if agg else 0,
                tags=inst.get("tags", {}) or {},
                state=inst.get("state"),
                region=inst.get("region") or region,
                account_id=inst.get("account_id"),
                observed_cost=resource_costs.get((inst.get("account_id"), instance_id, inst.get("region") or region)),
                cost_window_days=14,
                inactive_hours=getattr(provider, "inactive_hours_over_window", lambda *args: None)(tenant_id, instance_id, config.IDLE_WINDOW_DAYS, config.IDLE_CPU_THRESHOLD),
            )
        )

    for database in rds_dbs:
        resource_id = database.get("resource_id") or database.get("DBInstanceIdentifier")
        if resource_id:
            metric = getattr(provider, "aggregate_over_window", lambda *args: None)(tenant_id, resource_id, "cpu_utilization", config.IDLE_WINDOW_DAYS)
            database["avg_cpu"] = metric["value"] if metric else None
            database["metric_samples"] = metric["samples"] if metric else 0
            database["inactive_hours"] = getattr(provider, "inactive_hours_over_window", lambda *args: None)(tenant_id, resource_id, config.IDLE_WINDOW_DAYS, config.IDLE_CPU_THRESHOLD)

    for function in lambda_fns:
        resource_id = function.get("resource_id") or function.get("function_name")
        if resource_id:
            metric = getattr(provider, "aggregate_over_window", lambda *args: None)(tenant_id, resource_id, "invocations", config.IDLE_WINDOW_DAYS, "sum")
            function["invocations"] = metric["value"] if metric else None
            function["metric_samples"] = metric["samples"] if metric else 0

    ctx = AnalysisContext(
        tenant_id=tenant_id,
        region=region,
        ec2=ec2,
        rds=rds_dbs,
        lambda_functions=lambda_fns,
        ebs=ebs_vols,
        resource_costs=resource_costs,
    )
    return ctx


def analyze_tenant(
    db: Session, tenant_id: str, region: str | None = None, request_id: str = "-"
) -> list[dict]:
    """Run every rule pack for a tenant, persist findings, and index them for RAG.

    Data source (Prometheus+aws-connector vs offline dev seed) is chosen by config.
    A connector failure raises ConnectorError (route → 502); a single rule failing
    is logged and skipped so the rest still run.
    """
    assert tenant_id, "tenant_id is required"  # tenant isolation

    provider = get_provider()
    # Connector failure here raises ConnectorError (mapped to 502 by the route).
    ctx = _build_context(provider, tenant_id, region)

    logger.info(
        "Analyzing tenant",
        extra={
            "tenant_id": tenant_id,
            "request_id": request_id,
            "service": "insight-engine",
            "endpoint": "analyze",
            "ec2_count": len(ctx.ec2),
        },
    )

    insights: list[dict] = []
    rag_records: list[dict] = []
    finding_resource_ids: set[str] = set()
    for rule in get_rules():
        try:
            for finding in rule.evaluate(ctx):
                stored = insight_repository.upsert_insight(db, finding)
                finding_resource_ids.add(finding["resource_id"])
                record = stored.to_dict()
                insights.append(record)
                rag_records.append(record)
        except Exception:  # noqa: BLE001 — one bad rule must not abort the run
            db.rollback()
            logger.exception(
                "Rule failed",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "service": "insight-engine",
                    "endpoint": "analyze",
                    "rule": getattr(rule, "id", "unknown"),
                },
            )

    discovered = (
        [(s.resource_id, "ec2", s.account_id, s.region) for s in ctx.ec2]
        + [(x.get("resource_id") or x.get("DBInstanceIdentifier"), "rds", x.get("account_id"), x.get("region") or region) for x in ctx.rds]
        + [(x.get("resource_id") or x.get("function_name"), "lambda", x.get("account_id"), x.get("region") or region) for x in ctx.lambda_functions]
    )
    for resource_id, resource_type, account_id, resource_region in discovered:
        if resource_id and resource_id not in finding_resource_ids:
            observed_cost = ctx.resource_costs.get((account_id, resource_id, resource_region))
            cost_evidence = (
                f"AWS Cost Explorer resource-attributed net spend was ${observed_cost:.8f} over the last 14 days."
                if observed_cost is not None
                else "AWS Cost Explorer did not return resource-level cost data for this resource in the analysis window."
            )
            healthy = insight_repository.upsert_insight(db, {
                "tenant_id": tenant_id, "aws_account_id": account_id, "region": resource_region,
                "resource_id": resource_id, "resource_type": resource_type, "severity": "info",
                "category": "health", "issue": "Healthy / No issues detected",
                "recommendation": "No action required based on the configured checks.", "confidence": "medium",
                "estimated_monthly_waste": 0.0,
                "evidence": f"AWS resource discovered and evaluated; no configured rule matched a problem in this analysis run. {cost_evidence} Runtime hours are No data available because AWS Cost Explorer does not report instance state duration. Missing telemetry can limit confidence.",
                "window_days": float(config.IDLE_WINDOW_DAYS), "status": "healthy",
            })
            insights.append(healthy.to_dict())
            rag_records.append(healthy.to_dict())

    # One batched Voyage request per analysis run avoids exhausting the provider
    # quota when a tenant has many resources.
    rag_service.index_insights(rag_records, region=region)

    logger.info(
        "Analysis complete",
        extra={
            "tenant_id": tenant_id,
            "request_id": request_id,
            "service": "insight-engine",
            "endpoint": "analyze",
            "insights_found": len(insights),
        },
    )
    return insights
