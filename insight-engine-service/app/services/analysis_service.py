import logging

from sqlalchemy.orm import Session

from .. import config
from ..db import insight_repository
from ..rules.base import AnalysisContext, Ec2Signal
from ..rules.registry import get_rules
from ..sources.provider import get_provider
from . import rag_service

logger = logging.getLogger("insight-engine")


def _build_context(provider, tenant_id: str, region: str | None) -> AnalysisContext:
    """Gather per-tenant signals once, shared across every rule pack."""
    instances = provider.list_ec2_instances(tenant_id, region=region)
    rds_dbs = getattr(provider, "list_rds_databases", lambda t, region=None: [])(tenant_id, region=region)
    lambda_fns = getattr(provider, "list_lambda_functions", lambda t, region=None: [])(tenant_id, region=region)

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
            )
        )
    return AnalysisContext(tenant_id=tenant_id, region=region, ec2=ec2, rds=rds_dbs)


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
    for rule in get_rules():
        try:
            for finding in rule.evaluate(ctx):
                stored = insight_repository.upsert_insight(db, finding)
                record = stored.to_dict()
                insights.append(record)
                # RAG: index every finding (no-op unless Pinecone is configured).
                rag_service.index_insight(record, region=region)
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
