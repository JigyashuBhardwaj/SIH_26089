"""
Typed request/response models for the Phase 5E-B `GET /services` and
`GET /services/{service_id}` routes.

Deliberately separate from `app.models.service.Service` (the SQLAlchemy
model) — no route ever returns that model directly.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServicePublic(BaseModel):
    """Safe, public view of a `Service` catalogue entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    category: str
    is_active: bool = Field(alias="isActive")


class ServiceListResponse(BaseModel):
    """Paginated envelope for `GET /services`."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[ServicePublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
