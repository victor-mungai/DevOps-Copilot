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
import requests
import time
import threading
from typing import Optional

logger = logging.getLogger("insight-engine")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "devops-copilot")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# In-memory local fallback store (tenant_id -> list of doc dicts)
_local_rag_store: dict[str, list[dict]] = {}
_rag_stats: dict[str, dict] = {}
_rag_errors: dict[str, str] = {}
_embedding_cache: dict[tuple[str, str, str], tuple[float, list[float]]] = {}
_embedding_lock = threading.Lock()
_embedding_calls: list[float] = []
_EMBEDDING_CACHE_SECONDS = int(os.getenv("RAG_EMBEDDING_CACHE_SECONDS", "300"))
_EMBEDDING_MAX_BATCH = int(os.getenv("VOYAGE_MAX_BATCH", "32"))
_VOYAGE_REQUESTS_PER_MINUTE = int(os.getenv("VOYAGE_REQUESTS_PER_MINUTE", "3"))


def rag_enabled() -> bool:
    return bool(PINECONE_API_KEY and VOYAGE_API_KEY) or bool(_local_rag_store)


def diagnostics(tenant_id: str) -> dict:
    """Safe operational diagnostics; never returns keys or document content."""
    local = _local_rag_store.get(tenant_id, [])
    stats = _rag_stats.get(tenant_id, {})
    index = _get_index()
    pinecone_count = None
    if index is not None:
        try:
            index_stats = index.describe_index_stats()
            namespaces = index_stats.get("namespaces", {}) if isinstance(index_stats, dict) else getattr(index_stats, "namespaces", {})
            namespace_stats = namespaces.get(tenant_id, {}) if namespaces else {}
            pinecone_count = namespace_stats.get("vector_count", 0) if isinstance(namespace_stats, dict) else getattr(namespace_stats, "vector_count", 0)
        except Exception as exc:
            _rag_errors[tenant_id] = f"Pinecone stats failed: {type(exc).__name__}"
    return {
        "tenant_id": tenant_id,
        "backend": "pinecone" if (index is not None and VOYAGE_API_KEY) else "local_fallback",
        "pinecone_connected": bool(index is not None),
        "pinecone_namespace_vector_count": pinecone_count,
        "error": _rag_errors.get(tenant_id) or _rag_errors.get("__global__"),
        "namespace": tenant_id,
        "ingestion_count": stats.get("pinecone_ingestion_count", 0) if index is not None else stats.get("ingestion_count", len(local)),
        "retrieval_count": stats.get("retrieval_count", 0),
        "document_ids": stats.get("document_ids", [])[-20:],
        "metadata_fields": ["tenant_id", "region", "resource_type", "resource_id", "severity", "category", "timestamp", "source"],
    }


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
    if not texts:
        return []
    now = time.monotonic()
    cache_key = (input_type, VOYAGE_MODEL, "\n".join(texts))
    if len(texts) == 1:
        cached = _embedding_cache.get(cache_key)
        if cached and now - cached[0] < _EMBEDDING_CACHE_SECONDS:
            return [cached[1]]
    try:
        # Keep requests below the account quota. Batching is preferred; this
        # guard protects query traffic when several users refresh together.
        with _embedding_lock:
            cutoff = now - 60
            _embedding_calls[:] = [stamp for stamp in _embedding_calls if stamp > cutoff]
            if len(_embedding_calls) >= _VOYAGE_REQUESTS_PER_MINUTE:
                wait_for = 60 - (now - _embedding_calls[0])
                if wait_for > 0:
                    time.sleep(wait_for)
                    now = time.monotonic()
                    _embedding_calls[:] = [stamp for stamp in _embedding_calls if stamp > now - 60]
            _embedding_calls.append(time.monotonic())
        for attempt in range(3):
            response = requests.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {VOYAGE_API_KEY}"},
                json={"input": texts, "model": VOYAGE_MODEL, "input_type": input_type},
                timeout=30,
            )
            if response.status_code != 429:
                response.raise_for_status()
                return [item["embedding"] for item in response.json().get("data", [])]
            if attempt < 2:
                retry_after = response.headers.get("Retry-After")
                time.sleep(min(float(retry_after) if retry_after else 2 ** attempt, 30))
        response.raise_for_status()
        return []
        
    except Exception as exc:  # noqa: BLE001
        _rag_errors["__global__"] = f"Voyage embedding failed: {type(exc).__name__}"
        logger.warning("Voyage embedding failed: %s", exc)
        return None


def _embed_many(texts: list[str], input_type: str) -> Optional[list[list[float]]]:
    """Embed in provider-sized batches; one analysis run is not one request per finding."""
    result: list[list[float]] = []
    for offset in range(0, len(texts), _EMBEDDING_MAX_BATCH):
        batch = texts[offset : offset + _EMBEDDING_MAX_BATCH]
        embeddings = _embed(batch, input_type=input_type)
        if embeddings is None or len(embeddings) != len(batch):
            return None
        result.extend(embeddings)
    return result


def _insight_text(record: dict) -> str:
    return (
        f"{record.get('issue')} on {record.get('resource_type')} "
        f"{record.get('resource_id')} ({record.get('instance_type')}). "
        f"Category {record.get('category')}, severity {record.get('severity')}, "
        f"confidence {record.get('confidence')}. "
        f"Avg CPU {record.get('avg_cpu')}%. "
        f"Estimated monthly waste ${record.get('estimated_monthly_waste')}. "
        f"Observed AWS resource cost ${record.get('observed_cost')}; "
        f"runtime hours: {record.get('hours_run', 'No data available')}. "
        f"Recommendation: {record.get('recommendation')}."
    )


def index_insight(record: dict, region: Optional[str] = None) -> None:
    index_insights([record], region=region)


def index_insights(records: list[dict], region: Optional[str] = None) -> None:
    """Batch insight embeddings and upsert them into one tenant namespace."""
    records = [record for record in records if record.get("tenant_id")]
    if not records:
        return
    tenant_ids = {record["tenant_id"] for record in records}
    if len(tenant_ids) != 1:
        raise ValueError("RAG batch must contain one tenant")
    tenant_id = records[0]["tenant_id"]
    prepared = []
    stats = _rag_stats.setdefault(tenant_id, {"ingestion_count": 0, "retrieval_count": 0, "document_ids": []})
    tenant_store = _local_rag_store.setdefault(tenant_id, [])
    for record in records:
        text = _insight_text(record)
        metadata = {
            "tenant_id": tenant_id, "region": region or record.get("region") or "",
            "resource_type": record.get("resource_type", ""), "resource_id": record.get("resource_id", ""),
            "severity": record.get("severity", ""), "category": record.get("category", ""),
            "timestamp": record.get("created_at") or "", "source": "insight", "text": text,
        }
        doc_id = f"insight::{record['id']}"
        prepared.append((doc_id, text, metadata))
        if not any(item["metadata"].get("resource_id") == record.get("resource_id") and item["metadata"].get("category") == record.get("category") for item in tenant_store):
            tenant_store.append({"text": text, "metadata": metadata, "source": "insight", "score": 0.95})
            stats["ingestion_count"] += 1
            stats["document_ids"].append(doc_id)

    index = _get_index()
    if index is None or not VOYAGE_API_KEY:
        return
    embeddings = _embed_many([item[1] for item in prepared], input_type="document")
    if not embeddings:
        return
    try:
        index.upsert(
            vectors=[{"id": item[0], "values": embeddings[idx], "metadata": item[2]} for idx, item in enumerate(prepared)],
            namespace=tenant_id,
        )
        stats["pinecone_ingestion_count"] = stats.get("pinecone_ingestion_count", 0) + len(prepared)
        logger.info("RAG_INGEST tenant=%s backend=pinecone namespace=%s count=%s metadata_fields=%s", tenant_id, tenant_id, len(prepared), sorted(prepared[0][2].keys()))
    except Exception as exc:
        logger.warning("Pinecone batch upsert failed: %s", exc)


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
    stats = _rag_stats.setdefault(tenant_id, {"ingestion_count": 0, "retrieval_count": 0, "document_ids": []})

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
                    stats["retrieval_count"] += len(out)
                    logger.info("RAG_RETRIEVE tenant=%s namespace=%s count=%s", tenant_id, tenant_id, len(out))
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
    result = matches_local[:top_k]
    stats["retrieval_count"] += len(result)
    logger.info("RAG_RETRIEVE tenant=%s namespace=%s backend=local_fallback count=%s", tenant_id, tenant_id, len(result))
    return result
