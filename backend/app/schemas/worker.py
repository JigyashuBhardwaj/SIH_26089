"""
Typed response models for the Phase 5E-D worker-related read routes:
`GET /associations/me/workers`, `GET /workers/me`, `GET /federation/me/workers`.

Exposes ONLY fields that exist on the current, locked Phase 5C `Worker`
model. Per the Phase 5E-D reconciliation: `Worker.address`, `.pincode`,
`.rating`, and `.total_jobs_completed` do NOT exist in the current
database schema and are deliberately NOT included here — adding them
(worker location/statistics data for future matching) is explicitly out
of scope for this phase.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkerStatus


class WorkerPublic(BaseModel):
    """Safe, public view of a `Worker`. Never includes `password_hash` or Account internals."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    account_id: UUID = Field(alias="accountId")
    association_id: UUID = Field(alias="associationId")
    worker_code: str = Field(alias="workerCode")
    full_name: str = Field(alias="fullName")
    phone: str | None = Field(alias="phoneNumber")
    status: WorkerStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WorkerListResponse(BaseModel):
    """Paginated envelope for a worker list."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkerPublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
