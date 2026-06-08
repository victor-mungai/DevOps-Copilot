from typing import Optional

from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CreateTenantResponse(BaseModel):
    tenant_id: str
    external_id: str


class OnboardingLinkResponse(BaseModel):
    onboarding_url: str


class VerifyRoleRequest(BaseModel):
    role_arn: str = Field(..., min_length=20)
    region: Optional[str] = None


class VerifyRoleResponse(BaseModel):
    status: str
    account_id: str
    role_arn: str
    tenant_id: str
