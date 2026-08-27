CREATE TABLE IF NOT EXISTS workspace_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(320) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'member',
    status VARCHAR(30) NOT NULL DEFAULT 'invited',
    auth_user_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_workspace_users_tenant_email UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS ix_workspace_users_tenant_id ON workspace_users (tenant_id);
CREATE INDEX IF NOT EXISTS ix_workspace_users_auth_user_id ON workspace_users (auth_user_id);
