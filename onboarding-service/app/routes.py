import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db.connection import get_db
from .db.models import AwsAccount, WorkspaceUser
from .models import (
    CreateTenantRequest,
    CreateTenantResponse,
    OnboardingLinkResponse,
    VerifyRoleRequest,
    VerifyRoleResponse,
    CreateWorkspaceUserRequest,
    UpdateWorkspaceUserRequest,
    WorkspaceUserResponse,
)
from .services.aws_verification import assume_role_and_get_account_id
from .services.link_generator import generate_onboarding_link
from .services.tenant_service import create_tenant, get_tenant

router = APIRouter()


def _require_tenant_scope(tenant_id: str, x_tenant_id: str | None) -> None:
    if not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Tenant-ID header is required")
    if x_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _user_response(user: WorkspaceUser) -> WorkspaceUserResponse:
    return WorkspaceUserResponse(
        id=str(user.id), tenant_id=str(user.tenant_id), name=user.name, email=user.email,
        role=user.role, status=user.status, auth_user_id=user.auth_user_id,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


def _last_owner(db: Session, tenant_id, user: WorkspaceUser) -> bool:
    if user.role != "owner":
        return False
    return db.query(WorkspaceUser).filter(
        WorkspaceUser.tenant_id == tenant_id,
        WorkspaceUser.role == "owner",
        WorkspaceUser.status != "disabled",
    ).count() <= 1


@router.get("/health")
@router.get("/")
def health():
    return {"status": "healthy", "service": "onboarding"}


@router.post("/tenants", response_model=CreateTenantResponse)
def create_tenant_endpoint(
    payload: CreateTenantRequest, db: Session = Depends(get_db)
):
    tenant = create_tenant(db, payload.name)
    return CreateTenantResponse(
        tenant_id=str(tenant.id), external_id=tenant.external_id
    )


@router.get("/tenants/connected")
def list_connected_tenants(db: Session = Depends(get_db)):
    """Tenants with a verified AWS account. Used by the metrics-collector to
    discover who to schedule collection for, instead of a hardcoded env list."""
    rows = db.query(AwsAccount).filter(AwsAccount.status == "connected").all()
    return {
        "tenants": [
            {
                "tenant_id": str(r.tenant_id),
                "account_id": r.account_id,
                "region": r.region,
            }
            for r in rows
        ]
    }


@router.get("/tenants/{tenant_id}/accounts")
def list_tenant_accounts(tenant_id: str, db: Session = Depends(get_db)):
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    rows = (
        db.query(AwsAccount)
        .filter(AwsAccount.tenant_id == tenant.id)
        .order_by(AwsAccount.created_at.asc())
        .all()
    )
    return {
        "tenant_id": str(tenant.id),
        "accounts": [
            {
                "id": str(row.id),
                "account_id": row.account_id,
                "role_arn": row.role_arn,
                "region": row.region,
                "status": row.status,
                "last_verified_at": row.last_verified_at.isoformat()
                if row.last_verified_at
                else None,
            }
            for row in rows
        ],
    }


@router.get("/tenants/{tenant_id}/users", response_model=list[WorkspaceUserResponse])
def list_workspace_users(
    tenant_id: str,
    x_tenant_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    _require_tenant_scope(tenant_id, x_tenant_id)
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    rows = db.query(WorkspaceUser).filter(WorkspaceUser.tenant_id == tenant.id).order_by(WorkspaceUser.created_at.asc()).all()
    return [_user_response(row) for row in rows]


@router.post("/tenants/{tenant_id}/users", response_model=WorkspaceUserResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_user(
    tenant_id: str,
    payload: CreateWorkspaceUserRequest,
    x_tenant_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    _require_tenant_scope(tenant_id, x_tenant_id)
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    email = payload.email.strip().lower()
    existing = db.query(WorkspaceUser).filter(WorkspaceUser.tenant_id == tenant.id, WorkspaceUser.email == email).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists in the workspace")
    user = WorkspaceUser(
        tenant_id=tenant.id, name=payload.name.strip(), email=email,
        role=payload.role, status=payload.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.patch("/tenants/{tenant_id}/users/{user_id}", response_model=WorkspaceUserResponse)
def update_workspace_user(
    tenant_id: str,
    user_id: str,
    payload: UpdateWorkspaceUserRequest,
    x_tenant_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    _require_tenant_scope(tenant_id, x_tenant_id)
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    user = db.query(WorkspaceUser).filter(WorkspaceUser.tenant_id == tenant.id, WorkspaceUser.id == user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace user not found")
    changing_owner = payload.role is not None and payload.role != "owner"
    disabling_owner = payload.status == "disabled"
    if (changing_owner or disabling_owner) and _last_owner(db, tenant.id, user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The last active workspace owner cannot be changed or disabled")
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.delete("/tenants/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_user(
    tenant_id: str,
    user_id: str,
    x_tenant_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    _require_tenant_scope(tenant_id, x_tenant_id)
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    user = db.query(WorkspaceUser).filter(WorkspaceUser.tenant_id == tenant.id, WorkspaceUser.id == user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace user not found")
    if _last_owner(db, tenant.id, user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The last active workspace owner cannot be removed")
    db.delete(user)
    db.commit()


@router.get(
    "/tenants/{tenant_id}/onboarding-link", response_model=OnboardingLinkResponse
)
def get_onboarding_link(tenant_id: str, db: Session = Depends(get_db)):
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    onboarding_url = generate_onboarding_link(tenant.external_id)
    return OnboardingLinkResponse(onboarding_url=onboarding_url)


@router.post("/tenants/{tenant_id}/verify", response_model=VerifyRoleResponse)
def verify_role(
    tenant_id: str, payload: VerifyRoleRequest, db: Session = Depends(get_db)
):
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not tenant.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ExternalId is required for verification",
        )

    try:
        account_id = assume_role_and_get_account_id(
            payload.role_arn, tenant.external_id, payload.region
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AssumeRole failed: {exc}",
        ) from exc

    # A workspace may connect more than one AWS account. Upsert only the
    # verified account, never replace another account in the same workspace.
    aws_account = (
        db.query(AwsAccount)
        .filter(AwsAccount.tenant_id == tenant.id)
        .filter(AwsAccount.account_id == account_id)
        .one_or_none()
    )
    if not aws_account:
        aws_account = AwsAccount(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            role_arn=payload.role_arn,
            account_id=account_id,
            region=payload.region,
            status="connected",
            last_verified_at=dt.datetime.utcnow(),
        )
        db.add(aws_account)
    else:
        aws_account.role_arn = payload.role_arn
        aws_account.account_id = account_id
        aws_account.region = payload.region
        aws_account.status = "connected"
        aws_account.last_verified_at = dt.datetime.utcnow()

    db.commit()

    return VerifyRoleResponse(
        status=aws_account.status,
        account_id=account_id,
        role_arn=payload.role_arn,
        tenant_id=str(tenant.id),
    )
