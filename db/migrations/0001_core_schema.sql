-- DevOps Copilot — core schema (Sprint 2 first run)
-- Target: Supabase / PostgreSQL 13+
-- Apply this BEFORE starting any service. Idempotent (safe to re-run).
--
-- Shared by onboarding-service (writer) and aws-connector-service (reader).
-- The insights table is owned by insight-engine-service.

-- gen_random_uuid() lives in pgcrypto on older PGs; it's in core on Supabase.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- tenants  (authoritative model: onboarding-service)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    external_id VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_tenants_external_id ON tenants (external_id);

-- ---------------------------------------------------------------------------
-- aws_accounts  (onboarding writes status='connected' on verify; connector reads it)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aws_accounts (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants (id),
    account_id       VARCHAR(20),
    role_arn         TEXT NOT NULL,
    region           VARCHAR(50),
    status           VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_aws_accounts_tenant_id ON aws_accounts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_aws_accounts_status   ON aws_accounts (status);

-- ---------------------------------------------------------------------------
-- insights  (owned by insight-engine-service)
-- tenant_id is a free-form text key (matches String column in the ORM); no FK
-- so the insight engine stays decoupled from the onboarding schema.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS insights (
    id                      VARCHAR PRIMARY KEY,
    tenant_id               VARCHAR NOT NULL,
    resource_id             VARCHAR NOT NULL,
    resource_type           VARCHAR NOT NULL,
    severity                VARCHAR NOT NULL,
    category                VARCHAR NOT NULL,
    issue                   VARCHAR NOT NULL,
    recommendation          VARCHAR NOT NULL,
    confidence              VARCHAR NOT NULL,
    estimated_monthly_waste DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_cpu                 DOUBLE PRECISION,
    instance_type           VARCHAR,
    window_days             DOUBLE PRECISION,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_insights_tenant_id   ON insights (tenant_id);
CREATE INDEX IF NOT EXISTS ix_insights_resource_id ON insights (resource_id);
CREATE INDEX IF NOT EXISTS ix_insights_created_at  ON insights (created_at);
