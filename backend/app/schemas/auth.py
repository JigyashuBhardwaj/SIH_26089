"""
Typed request/response models for the `/auth` routes.

`AccountPublic` is the one place that defines what "safe" Account
information means — it deliberately has no `password_hash` field at all
(not just one that gets excluded at serialization time), so there is no
way for a route to accidentally leak it through this model.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AccountRole


class LoginRequest(BaseModel):
    login_id: str
    password: str


class AccountPublic(BaseModel):
    """Safe, public view of an Account — never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login_id: str
    role: AccountRole
    is_active: bool
    association_id: UUID | None
    federation_id: UUID | None
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: AccountPublic
