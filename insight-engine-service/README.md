# Insight Engine Service

Generates AI-powered infrastructure insights for DevOps Copilot tenants. Sprint 2
delivers the first complete value loop: **metrics → idle-EC2 rule → structured
insight → cost estimate → LLM explanation**, all strictly tenant-scoped.

## What it does
- **Feature 1 — Idle EC2 rule**: flags EC2 instances whose average CPU is below
  the threshold (default 5%) over the window (default 7 days), with enough
  samples to trust the verdict.
- **Feature 2 — Cost estimate**: approximate monthly waste from a static lookup
  table (`app/rules/cost_table.py`). No pricing API yet, by design.
- **Feature 5 — Secure LLM explanation**: a context-only system prompt that always
  answers with Summary / Root Cause / Impact / Recommendation, with input
  sanitization and a hard question-length cap. Falls back to a deterministic
  templated explanation when no `ANTHROPIC_API_KEY` is set.
- **Feature 6 — Tenant isolation**: every query is tenant-scoped; a path tenant_id
  that disagrees with the gateway-injected `X-Tenant-ID` is rejected (403).

## Endpoints
- `GET  /health`
- `POST /insights/{tenant_id}/analyze` — run the rule, persist findings, return them
- `GET  /insights/{tenant_id}?limit=&offset=` — list insights (paginated)
- `POST /insights/{tenant_id}/explain` — `{ "question": "...", "insight_id?": "..." }`
  → `{ "answer", "model", "insight_id" }`

Through the gateway these are `/v1/insights/...`.

## Data source (`METRIC_SOURCE`)
- `prometheus` (default): authoritative EC2 list from **aws-connector**, CPU
  aggregate from **Prometheus** (`avg_over_time(cpu_utilization{tenant,resource}[7d])`).
- `dev`: fully offline — both come from a synthetic seed file. Lets the whole
  loop run with **no Docker / Prometheus / AWS**.

## Run locally (offline dev loop)
```
python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
python scripts/seed_dev.py --tenant <tenant_id>      # writes seed_metrics.json
set METRIC_SOURCE=dev
uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
```
Then: `POST /insights/<tenant_id>/analyze` → expect one idle `t3.large`
(~$68/mo), then `POST /insights/<tenant_id>/explain`.

## Config
See `.env.example`. Key vars: `METRIC_SOURCE`, `SEED_FILE`, `PROMETHEUS_URL`,
`AWS_CONNECTOR_BASE_URL`, `DATABASE_URL`, `IDLE_CPU_THRESHOLD`, `IDLE_WINDOW_DAYS`,
`IDLE_MIN_SAMPLES`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `MAX_QUESTION_LENGTH`.

## Known follow-ups (Phase 2)
- Pinecone (namespace = tenant_id) + Voyage embeddings for RAG retrieval
- `conversations` table + last-10 retrieval + 50-message summarization
- Prometheus remote-write seeder for realistic backdated history
