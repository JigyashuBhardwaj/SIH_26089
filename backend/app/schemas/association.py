"""
Typed response models for the Phase 5E-D `GET /federation/me/associations`
route.

Exposes only the fields that exist on the current, locked Phase 5C
`Association` model (`pincode_coverage` is explicitly not modeled at all,
per that model's own docstring, so there is nothing to omit here).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssociationPublic(BaseModel):
    """Safe, public view of an `Association`."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    federation_id: UUID = Field(alias="federationId")
    name: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class AssociationListResponse(BaseModel):
    """Paginated envelope for `GET /federation/me/associations`."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[AssociationPublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
