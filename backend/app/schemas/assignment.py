"""
Typed request/response models for the Phase 5E-D `GET /workers/me/assignments`
route and the Phase 5E-E `POST /associations/me/requests/{request_id}/assignments`
route.

Exposes/accepts ONLY fields that exist on the current, locked Phase 5C
`Assignment` model. There is deliberately NO `createdAt` field here:
`Assignment` has no `created_at` column (see the model's own docstring —
`assigned_at` serves as this row's creation timestamp), and this schema
must not alias `assigned_at` as `createdAt` or invent one.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssignmentStatus


class AssignmentCreate(BaseModel):
    """
    `POST /associations/me/requests/{request_id}/assignments` request
    body. Only the one field a client may supply — `id`, `requestId`
    (taken from the path), `assignedBy` (derived from the authenticated
    admin), `status`, `assignedAt`, `respondedAt`, `updatedAt` are never
    accepted here; the server always computes them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    worker_id: UUID = Field(alias="workerId")


class AssignmentPublic(BaseModel):
    """Safe, public view of an `Assignment` belonging to the authenticated worker."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    request_id: UUID = Field(alias="requestId")
    worker_id: UUID = Field(alias="workerId")
    assigned_by: UUID = Field(alias="assignedBy")
    status: AssignmentStatus
    assigned_at: datetime = Field(alias="assignedAt")
    responded_at: datetime | None = Field(alias="respondedAt")
    updated_at: datetime = Field(alias="updatedAt")


class AssignmentListResponse(BaseModel):
    """Paginated envelope for `GET /workers/me/assignments`."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[AssignmentPublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
