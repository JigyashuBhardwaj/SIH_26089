"""
Typed response model for the Phase 5E-B `GET /users/me` route.

Deliberately separate from `app.models.user_profile.UserProfile` (the
SQLAlchemy model) — no route ever returns that model directly. Never
includes any authentication information.

Per the locked Phase 5E-B decision: `defaultAddress` is deliberately NOT
included here. The locked Phase 5C `UserProfile` schema has no address
column, and adding one is out of scope for this phase (no schema
changes). A future phase that adds address data to `UserProfile` can
extend this response then.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfilePublic(BaseModel):
    """Safe, public view of the authenticated user's own `UserProfile`."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    account_id: UUID = Field(alias="accountId")
    full_name: str = Field(alias="fullName")
    phone: str | None = Field(alias="phoneNumber")
