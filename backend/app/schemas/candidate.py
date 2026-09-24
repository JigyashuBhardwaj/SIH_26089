"""
Phase 5E-H: typed response models for the read-only candidate discovery
route, `GET /associations/me/requests/{request_id}/candidates`.

A `CandidatePublic` is NOT a `WorkerPublic` — it deliberately narrows to
the fields an Association Admin needs to understand *why* a worker
appears in the list (see `app/api/associations.py`'s
`list_candidates_for_request` for the eligibility/ranking rules this
schema surfaces), and adds two fields that don't exist on `Worker` at
all: `activeAssignmentCount` and `samePincode`, both computed per-request
at query time. There is deliberately no opaque numerical "score" field —
the three ranking factors (`samePincode`, `activeAssignmentCount`,
`rating`) are exposed directly instead, exactly as the locked spec
requires.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidatePublic(BaseModel):
    """
    One eligible Worker, ranked for a specific ServiceRequest. Built by
    hand from a query row in `associations.py` — NOT via
    `model_validate(worker)` — since `activeAssignmentCount` and
    `samePincode` are not attributes of `Worker` itself.
    """

    model_config = ConfigDict(populate_by_name=True)

    worker_id: UUID = Field(alias="workerId")
    worker_code: str = Field(alias="workerCode")
    full_name: str = Field(alias="fullName")
    phone: str | None = Field(alias="phoneNumber")
    address: str
    pincode: str
    rating: Decimal
    total_jobs_completed: int = Field(alias="totalJobsCompleted")
    active_assignment_count: int = Field(alias="activeAssignmentCount")
    same_pincode: bool = Field(alias="samePincode")


class CandidateListResponse(BaseModel):
    """Paginated envelope for the candidate discovery list."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[CandidatePublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
