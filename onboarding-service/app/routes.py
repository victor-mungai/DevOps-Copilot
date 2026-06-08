import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db.connection import get_db
from .db.models import AwsAccount
from .models import (
    CreateTenantRequest,
    CreateTenantResponse,
    OnboardingLinkResponse,
    VerifyRoleRequest,
    VerifyRoleResponse,
)
from .services.aws_verification import assume_role_and_get_account_id
from .services.link_generator import generate_onboarding_link
from .services.tenant_service import create_tenant, get_tenant

router = APIRouter()


@router.post("/tenants", response_model=CreateTenantResponse)
def create_tenant_endpoint(
    payload: CreateTenantRequest, db: Session = Depends(get_db)
):
    tenant = create_tenant(db, payload.name)
    return CreateTenantResponse(
        tenant_id=str(tenant.id), external_id=tenant.external_id
    )


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
        existing = (
            db.query(AwsAccount)
            .filter(AwsAccount.tenant_id == tenant.id)
            .one_or_none()
        )
        if existing:
            existing.status = "failed"
            existing.last_verified_at = dt.datetime.utcnow()
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AssumeRole failed: {exc}",
        ) from exc

    aws_account = (
        db.query(AwsAccount).filter(AwsAccount.tenant_id == tenant.id).one_or_none()
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
