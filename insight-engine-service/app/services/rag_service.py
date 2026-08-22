"""Retrieval-Augmented Generation pipeline (Sprint 3).

Flow: insight generated → embed → upsert to Pinecone (namespace = tenant_id) →
retrieve relevant context at query time → feed the AI context builder.

Everything degrades gracefully: if PINECONE_API_KEY / VOYAGE_API_KEY (or the
client libs) are absent, indexing and retrieval become no-ops and the platform
keeps working with DB + live metrics context. Wire real keys to activate — no
code change needed.

Tenant isolation is enforced by Pinecone namespaces (one per tenant_id); every
vector also carries tenant_id/region/resource metadata for filtered retrieval.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger("insight-engine")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "devops-copilot")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# In-memory local fallback store (tenant_id -> list of doc dicts)
_local_rag_store: dict[str, list[dict]] = {}


def rag_enabled() -> bool:
    return True  # RAG active either via Pinecone or local vector fallback


_index = None


def _get_index():
    """Lazily create the Pinecone index handle. Returns None (no-op) on any
    failure, including the client lib not being installed."""
    global _index
    if _index is not None:
        return _index
    if not PINECONE_API_KEY:
        return None
    try:
        from pinecone import Pinecone  # lazy: only needed when configured

        pc = Pinecone(api_key=PINECONE_API_KEY)
        _index = pc.Index(PINECONE_INDEX)
        return _index
    except Exception as exc:  # noqa: BLE001 — RAG is additive, never fatal
        logger.warning("Pinecone unavailable: %s", exc)
        return None


def _embed(texts: list[str], input_type: str = "document") -> Optional[list[list[float]]]:
    if not VOYAGE_API_KEY:
        return None
    try:
        import voyageai  # lazy

        client = voyageai.Client(api_key=VOYAGE_API_KEY)
        result = client.embed(texts, model=VOYAGE_MODEL, input_type=input_type)
        return result.embeddings
    except Exception as exc:  # noqa: BLE001
        logger.warning("Voyage embedding failed: %s", exc)
        return None


def _insight_text(record: dict) -> str:
    return (
        f"{record.get('issue')} on {record.get('resource_type')} "
        f"{record.get('resource_id')} ({record.get('instance_type')}). "
        f"Category {record.get('category')}, severity {record.get('severity')}, "
        f"confidence {record.get('confidence')}. "
        f"Avg CPU {record.get('avg_cpu')}%. "
        f"Estimated monthly waste ${record.get('estimated_monthly_waste')}. "
        f"Recommendation: {record.get('recommendation')}."
    )


def index_insight(record: dict, region: Optional[str] = None) -> None:
    """Embed and upsert one insight into the tenant's namespace. Uses Pinecone or local store."""
    tenant_id = record.get("tenant_id")
    if not tenant_id:
        return
    text = _insight_text(record)
    metadata = {
        "tenant_id": tenant_id,
        "region": region or record.get("region") or "",
        "resource_type": record.get("resource_type", ""),
        "resource_id": record.get("resource_id", ""),
        "severity": record.get("severity", ""),
        "category": record.get("category", ""),
        "timestamp": record.get("created_at") or "",
        "source": "insight",
        "text": text,
    }

    # 1. Local Fallback In-Memory Store
    tenant_store = _local_rag_store.setdefault(tenant_id, [])
    # Avoid duplicate local indexing
    if not any(item["metadata"].get("resource_id") == record.get("resource_id") and item["metadata"].get("category") == record.get("category") for item in tenant_store):
        tenant_store.append({"text": text, "metadata": metadata, "source": "insight", "score": 0.95})

    # 2. Pinecone Remote Upsert (if configured)
    index = _get_index()
    if index is not None and VOYAGE_API_KEY:
        embeddings = _embed([text], input_type="document")
        if embeddings:
            try:
                index.upsert(
                    vectors=[
                        {"id": f"insight::{record['id']}", "values": embeddings[0], "metadata": metadata}
                    ],
                    namespace=tenant_id,
                )
            except Exception as exc:
                logger.warning("Pinecone upsert failed: %s", exc)


def index_document(
    tenant_id: str, doc_id: str, text: str, source: str, metadata: Optional[dict] = None
) -> None:
    """Generic upsert for runbooks / platform docs / conversation summaries."""
    meta = {"tenant_id": tenant_id, "source": source, "text": text, **(metadata or {})}
    tenant_store = _local_rag_store.setdefault(tenant_id, [])
    tenant_store.append({"text": text, "metadata": meta, "source": source, "score": 0.9})

    index = _get_index()
    if index is not None and VOYAGE_API_KEY:
        embeddings = _embed([text], input_type="document")
        if embeddings:
            try:
                index.upsert(
                    vectors=[{"id": f"{source}::{doc_id}", "values": embeddings[0], "metadata": meta}],
                    namespace=tenant_id,
                )
            except Exception as exc:
                logger.warning("Pinecone upsert (doc) failed: %s", exc)


def retrieve(
    tenant_id: str,
    query: str,
    region: Optional[str] = None,
    resource_id: Optional[str] = None,
    top_k: int = RAG_TOP_K,
) -> list[dict]:
    """Retrieve relevant context for a query from the tenant's namespace.

    Returns [{text, score, source, metadata}]. Tenant isolation is guaranteed by namespace.
    """
    assert tenant_id, "tenant_id is required"
    out: list[dict] = []

    # 1. Check Pinecone Index first if configured
    index = _get_index()
    if index is not None and VOYAGE_API_KEY:
        embeddings = _embed([query], input_type="query")
        if embeddings:
            flt: dict = {}
            if resource_id:
                flt["resource_id"] = {"$eq": resource_id}
            if region:
                flt["region"] = {"$eq": region}
            try:
                res = index.query(
                    vector=embeddings[0],
                    top_k=top_k,
                    namespace=tenant_id,
                    include_metadata=True,
                    filter=flt or None,
                )
                matches = res.get("matches", []) if isinstance(res, dict) else getattr(res, "matches", [])
                for m in matches:
                    meta = m.get("metadata", {}) if isinstance(m, dict) else getattr(m, "metadata", {})
                    score = m.get("score") if isinstance(m, dict) else getattr(m, "score", None)
                    out.append(
                        {
                            "text": meta.get("text", ""),
                            "score": score,
                            "source": meta.get("source", "insight"),
                            "metadata": meta,
                        }
                    )
                if out:
                    return out
            except Exception as exc:
                logger.warning("Pinecone query failed: %s", exc)

    # 2. Local Fallback Retrieval (strictly scoped to tenant_id namespace)
    tenant_store = _local_rag_store.get(tenant_id, [])
    q_words = set(query.lower().split())
    matches_local = []
    for item in tenant_store:
        meta = item["metadata"]
        if resource_id and meta.get("resource_id") != resource_id:
            continue
        if region and meta.get("region") and meta.get("region") != region:
            continue
        text_words = set(item["text"].lower().split())
        overlap = len(q_words.intersection(text_words))
        score = 0.5 + (0.05 * overlap)
        matches_local.append({**item, "score": min(0.99, score)})

    matches_local.sort(key=lambda x: x["score"], reverse=True)
    return matches_local[:top_k]
