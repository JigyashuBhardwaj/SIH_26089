"""
Typed response models for the worker-related read routes:
`GET /associations/me/workers`, `GET /workers/me`, `GET /federation/me/workers`.

Phase 5E-G adds the four worker profile/matching-data fields
(`address`, `pincode`, `rating`, `totalJobsCompleted`) established on the
`Worker` model in this same phase -- see `app/models/worker.py` for their
exact constraints. No matching/ranking logic reads them yet; this is a
read-only exposure of already-authoritative backend data.
"""

from datetime import datetime
from decimal import Decimal
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
    address: str
    pincode: str
    rating: Decimal
    total_jobs_completed: int = Field(alias="totalJobsCompleted")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WorkerListResponse(BaseModel):
    """Paginated envelope for a worker list."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkerPublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
