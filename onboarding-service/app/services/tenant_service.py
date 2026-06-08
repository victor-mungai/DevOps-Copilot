import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..db.models import Tenant


def create_tenant(db: Session, name: str) -> Tenant:
    tenant_id = uuid.uuid4()
    external_id = f"copilot-{tenant_id}"

    tenant = Tenant(id=tenant_id, name=name, external_id=external_id)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def get_tenant(db: Session, tenant_id: str) -> Optional[Tenant]:
    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        return None
    return db.get(Tenant, tenant_uuid)
