from typing import Literal, Optional

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
    region: str = Field(..., min_length=3, max_length=50)


class VerifyRoleResponse(BaseModel):
    status: str
    account_id: str
    role_arn: str
    tenant_id: str


class CreateWorkspaceUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=320)
    role: Literal["owner", "admin", "member", "viewer"] = "member"
    status: Literal["active", "invited", "disabled"] = "invited"


class UpdateWorkspaceUserRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[Literal["owner", "admin", "member", "viewer"]] = None
    status: Optional[Literal["active", "invited", "disabled"]] = None


class WorkspaceUserResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    email: str
    role: str
    status: str
    auth_user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
