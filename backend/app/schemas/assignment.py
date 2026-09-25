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


class AssignmentRequestSummary(BaseModel):
    """
    Phase 6E-A: a minimal, read-only snapshot of the ServiceRequest a
    Worker-facing Assignment belongs to -- exactly the fields the Worker
    app's MVP flow needs to show real job information (service name,
    requested date/time, address, pincode, human-readable request code)
    instead of a synthetic UUID-derived placeholder. Always computed
    fresh from the existing `ServiceRequest`/`Service` rows (joined in
    `app/api/workers.py::list_own_assignments`) -- never a second,
    independently-stored source of truth.
    """

    model_config = ConfigDict(populate_by_name=True)

    request_code: str = Field(alias="requestCode")
    service_name: str = Field(alias="serviceName")
    requested_date_time: datetime = Field(alias="requestedDateTime")
    address: str
    pincode: str


class WorkerAssignmentPublic(AssignmentPublic):
    """
    Phase 6E-A: the Worker-facing view of `GET /workers/me/assignments`,
    the same as `AssignmentPublic` plus `requestSummary`.

    Deliberately a SEPARATE schema from `AssignmentPublic` rather than an
    added field there -- `AssignmentPublic` is also the response shape
    for `accept`/`decline`/`cancel`/`complete`
    (`app/api/assignments.py`) and the association-admin
    assignment-creation route (`app/api/associations.py`); adding a field
    there would change every one of those existing, already-locked
    response shapes. This subclass touches none of them: it is used only
    by `GET /workers/me/assignments`.

    `request_summary` is `Optional`/defaulted only so that
    `WorkerAssignmentPublic.model_validate(assignment)` (which cannot see
    this joined data via plain attribute access) never fails before the
    route explicitly sets it -- for a real persisted Assignment row it is
    always populated in the actual HTTP response, since
    `Assignment.request_id` is `ON DELETE RESTRICT` and can never dangle.
    """

    request_summary: AssignmentRequestSummary | None = Field(
        alias="requestSummary", default=None
    )


class WorkerAssignmentListResponse(BaseModel):
    """Paginated envelope for `GET /workers/me/assignments`, using the enriched `WorkerAssignmentPublic` item shape."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkerAssignmentPublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
