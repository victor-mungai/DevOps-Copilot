import uuid
from typing import Optional

from sqlalchemy.orm import Session

from .models import AwsAccount, Tenant


def get_connected_account(db: Session, tenant_id: str) -> Optional[dict]:
    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        return None

    result = (
        db.query(AwsAccount, Tenant)
        .join(Tenant, Tenant.id == AwsAccount.tenant_id)
        .filter(AwsAccount.tenant_id == tenant_uuid)
        .filter(AwsAccount.status == "connected")
        .one_or_none()
    )
    if not result:
        return None

    aws_account, tenant = result
    return {
        "role_arn": aws_account.role_arn,
        "external_id": tenant.external_id,
        "region": aws_account.region,
    }
