"""Central AI context builder (Sprint 2.1).

Assembles everything the Copilot needs to answer, in one tenant-scoped place, in
this order: tenant validation → region/resource filter → insights (DB) → metrics
(Prometheus) → RAG (Pinecone, when configured). History is supplied by the caller
(sliding window). Everything is bounded to protect memory and token budget.
"""
import logging
import os

from sqlalchemy.orm import Session

from .. import config
from ..db import insight_repository
from ..sources.prometheus_source import PrometheusMetricSource

logger = logging.getLogger("insight-engine")

MAX_INSIGHTS_PER_QUERY = int(os.getenv("MAX_INSIGHTS_PER_QUERY", "20"))


def _rag_context(tenant_id: str, resource_id: str | None) -> list[str]:
    """Pinecone + Voyage RAG is a locked Phase-2 decision but not yet provisioned.

    Returns [] until PINECONE_API_KEY is configured, keeping the pipeline shape
    stable so real retrieval is a drop-in later. Never raises — RAG is additive.
    """
    if not os.getenv("PINECONE_API_KEY"):
        return []
    try:
        # Placeholder for: embed(question) -> pinecone.query(namespace=tenant_id)
        return []
    except Exception as exc:  # noqa: BLE001 — RAG must never break the answer
        logger.warning("RAG retrieval failed: %s", exc)
        return []


def build_ai_context(
    db: Session,
    tenant_id: str,
    region: str | None = None,
    resource_id: str | None = None,
    insight_id: str | None = None,
) -> dict:
    assert tenant_id, "tenant_id is required"  # tenant isolation, defense in depth

    all_insights = [
        row.to_dict()
        for row in insight_repository.list_insights(db, tenant_id, limit=MAX_INSIGHTS_PER_QUERY)
    ]

    # Region/resource filtering to scope the context.
    insights = all_insights
    if resource_id:
        scoped = [i for i in all_insights if i["resource_id"] == resource_id]
        insights = scoped or all_insights  # fall back so we can still answer

    primary = None
    if insight_id:
        got = insight_repository.get_insight(db, tenant_id, insight_id)
        primary = got.to_dict() if got else None
    if not primary:
        primary = insights[0] if insights else None

    # Live metric evidence for the focused resource.
    metrics: list[dict] = []
    if resource_id:
        try:
            agg = PrometheusMetricSource().avg_cpu_over_window(
                tenant_id, resource_id, config.IDLE_WINDOW_DAYS
            )
            if agg:
                metrics.append(
                    {
                        "resource_id": resource_id,
                        "metric": config.METRIC_NAME_CPU,
                        "avg": round(agg["avg"], 2),
                        "samples": agg["samples"],
                        "window_days": config.IDLE_WINDOW_DAYS,
                    }
                )
        except Exception as exc:  # noqa: BLE001 — metrics are best-effort context
            logger.warning("Metric context fetch failed for %s: %s", resource_id, exc)

    return {
        "tenant_id": tenant_id,
        "region": region,
        "resource_id": resource_id,
        "primary_insight_id": primary["id"] if primary else None,
        "primary_insight": primary,
        "insights": insights[:MAX_INSIGHTS_PER_QUERY],
        "metrics": metrics,
        "rag_context": _rag_context(tenant_id, resource_id),
    }
