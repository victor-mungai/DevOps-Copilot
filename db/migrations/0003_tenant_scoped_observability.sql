-- DevOps Copilot - tenant-scoped observability and cost hardening
-- Target: Supabase / PostgreSQL 13+
-- Idempotent migration for strict tenant/account/region scoping.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Insights must carry immutable tenant/account/region scope when AWS provides it.
ALTER TABLE insights ADD COLUMN IF NOT EXISTS aws_account_id VARCHAR;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS region VARCHAR;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS title VARCHAR;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS description VARCHAR;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS evidence VARCHAR;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active';
ALTER TABLE insights ADD COLUMN IF NOT EXISTS first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS last_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS occurrence_count DOUBLE PRECISION DEFAULT 1;

CREATE INDEX IF NOT EXISTS ix_insights_aws_account_id ON insights (aws_account_id);
CREATE INDEX IF NOT EXISTS ix_insights_region ON insights (region);

-- Cost records are owned by cost-collector-service and must always be scoped by
-- tenant + AWS linked account + region + usage type from Cost Explorer.
CREATE TABLE IF NOT EXISTS aws_costs (
    id              VARCHAR PRIMARY KEY,
    tenant_id       VARCHAR NOT NULL,
    aws_account_id  VARCHAR NOT NULL,
    billing_date    DATE NOT NULL,
    service_name    VARCHAR NOT NULL,
    region          VARCHAR NOT NULL,
    usage_type      VARCHAR NOT NULL,
    unblended_cost  DOUBLE PRECISION NOT NULL DEFAULT 0,
    amortized_cost  DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency        VARCHAR DEFAULT 'USD',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_aws_costs_tenant_billing UNIQUE (
        tenant_id,
        aws_account_id,
        billing_date,
        service_name,
        region,
        usage_type
    )
);

CREATE INDEX IF NOT EXISTS ix_aws_costs_tenant_id ON aws_costs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_aws_costs_aws_account_id ON aws_costs (aws_account_id);
CREATE INDEX IF NOT EXISTS ix_aws_costs_billing_date ON aws_costs (billing_date);
CREATE INDEX IF NOT EXISTS ix_aws_costs_service_name ON aws_costs (service_name);
CREATE INDEX IF NOT EXISTS ix_aws_costs_region ON aws_costs (region);
