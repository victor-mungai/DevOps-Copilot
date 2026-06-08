-- DevOps Copilot — conversation memory (Sprint 2 Feature 4)
-- Target: Supabase / PostgreSQL 13+
-- NOTE: not yet read/written by any service. This lands with Phase 2
-- (conversation memory). Safe to apply now so the schema is ready. Idempotent.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    role       VARCHAR(50) NOT NULL,      -- 'user' | 'assistant' | 'system'
    message    TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Memory optimization: the hot query is "last N messages for a (tenant, session)
-- ordered by created_at DESC". This composite index serves it directly.
CREATE INDEX IF NOT EXISTS ix_conversations_tenant_session_created
    ON conversations (tenant_id, session_id, created_at DESC);

-- Session summaries (Feature 4: summarize + archive sessions over 50 messages).
CREATE TABLE IF NOT EXISTS session_summaries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    session_id  VARCHAR(255) NOT NULL,
    summary     TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, session_id)
);
