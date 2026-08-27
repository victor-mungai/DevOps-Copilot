CREATE TABLE IF NOT EXISTS aws_resource_costs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    aws_account_id TEXT NOT NULL,
    billing_date DATE NOT NULL,
    service_name TEXT NOT NULL,
    region TEXT,
    resource_id TEXT NOT NULL,
    unblended_cost NUMERIC(18, 8) NOT NULL DEFAULT 0,
    net_unblended_cost NUMERIC(18, 8) NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    source TEXT NOT NULL DEFAULT 'AWS_COST_EXPLORER_GET_COST_AND_USAGE_WITH_RESOURCES',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_aws_resource_costs_scope UNIQUE (
        tenant_id, aws_account_id, billing_date, service_name, region, resource_id
    )
);

CREATE INDEX IF NOT EXISTS ix_aws_resource_costs_tenant_id ON aws_resource_costs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_aws_resource_costs_account_id ON aws_resource_costs (aws_account_id);
CREATE INDEX IF NOT EXISTS ix_aws_resource_costs_billing_date ON aws_resource_costs (billing_date);
CREATE INDEX IF NOT EXISTS ix_aws_resource_costs_resource_id ON aws_resource_costs (resource_id);
