import uuid
from typing import Optional

from sqlalchemy.orm import Session

from .models import AwsAccount, Tenant


def get_connected_accounts(db: Session, tenant_id: str) -> list[dict]:
    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        return None

    rows = (
        db.query(AwsAccount, Tenant)
        .join(Tenant, Tenant.id == AwsAccount.tenant_id)
        .filter(AwsAccount.tenant_id == tenant_uuid)
        .filter(AwsAccount.status == "connected")
        .all()
    )
    return [
        {
            "role_arn": aws_account.role_arn,
            "external_id": tenant.external_id,
            "region": aws_account.region,
            "account_id": aws_account.account_id,
        }
        for aws_account, tenant in rows
    ]


def get_connected_account(
    db: Session, tenant_id: str, account_id: str | None = None
) -> Optional[dict]:
    accounts = get_connected_accounts(db, tenant_id)
    if account_id:
        return next((account for account in accounts if account["account_id"] == account_id), None)
    return accounts[0] if len(accounts) == 1 else None
