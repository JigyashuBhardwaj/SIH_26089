"""
Typed request/response models for the Phase 7C-D worker-leave routes:
`POST /workers/me/leaves`, `GET /workers/me/leaves`.

Deliberately separate from `app.models.worker_leave.WorkerLeave` (the
SQLAlchemy model) — no route ever returns that model directly, and
`WorkerLeaveCreate` only accepts exactly the two fields a client is
allowed to set (`startAt`/`endAt`). Everything else (`id`, `workerId`,
`status`, `reviewedBy`, `reviewedAt`, `createdAt`, `updatedAt`) is owned
by the server: `workerId` is always the authenticated worker's own id
(never client-suppliable, mirroring `ServiceRequestCreate` never
accepting `userId`), `status` always starts at PENDING (Phase 7C-E's
approval endpoint is the only thing that ever changes it), and
`reviewedBy`/`reviewedAt` stay `None` until that same future approval.

Validation performed here is schema-level/stateless only, mirroring
`ServiceRequestCreate._validate_requested_date_time`'s own naive-datetime
rejection and the Phase 7C-C maximum-booking-horizon check it added:
naive-datetime rejection, `endAt >= startAt` (the "invalid interval"
case), and the 2-Asia/Kolkata-calendar-day minimum notice period (Phase
7C-C locked decision 13). Business rules that need a database read —
overlap with an existing PENDING/APPROVED leave, conflict with an
existing ACCEPTED assignment — cannot live here (a Pydantic schema has no
database session) and are enforced in `app/api/workers.py`'s route
function instead, using the existing `app.domain.leave_rules` primitives.
The annual 60-day quota is NOT checked anywhere in this phase — per the
locked Phase 7C-D product decisions, only APPROVED leave consumes quota,
and quota is an approval-time gate (Phase 7C-E), not a submission-time one.
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.leave_rules import to_kolkata_date
from app.models.worker_leave import LeaveStatus

# Phase 7C-C locked product decision 13: a worker must submit a leave
# request at least this many Asia/Kolkata calendar days before the leave
# starts. Exactly this many days ahead is valid (inclusive boundary,
# consistent with every other boundary convention in this codebase).
MINIMUM_LEAVE_NOTICE_DAYS = 2


class WorkerLeaveCreate(BaseModel):
    """
    `POST /workers/me/leaves` request body. Only the two fields a client
    may supply — `id`/`workerId`/`status`/`reviewedBy`/`reviewedAt`/
    `createdAt`/`updatedAt` are never accepted here; the server always
    computes them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    start_at: datetime = Field(alias="startAt")
    end_at: datetime = Field(alias="endAt")

    @field_validator("start_at", "end_at")
    @classmethod
    def _reject_naive_datetime(cls, value: datetime) -> datetime:
        """
        Reject a naive datetime outright (rather than silently guessing a
        timezone, which would create ambiguity), mirroring
        `ServiceRequestCreate._validate_requested_date_time`'s identical
        check.
        """
        if value.tzinfo is None:
            raise ValueError(
                "must be a timezone-aware ISO-8601 datetime "
                "(e.g. include a UTC offset or 'Z')"
            )
        return value

    @model_validator(mode="after")
    def _validate_interval_and_notice(self) -> "WorkerLeaveCreate":
        """
        Cross-field checks that need both `start_at` and `end_at`
        together, run only after both individually pass
        `_reject_naive_datetime` above:

        1. "Invalid interval" — `end_at` must not be before `start_at`.
           The database's own `ck_worker_leaves_end_at_after_start_at`
           CHECK constraint would also catch this, but rejecting it here
           gives a clean 422 instead of surfacing as an unhandled
           `IntegrityError`.
        2. The 2-Asia/Kolkata-calendar-day minimum notice period (Phase
           7C-C locked decision 13) — calendar-day arithmetic via
           `to_kolkata_date`, the same shared primitive the Phase 7C-C
           booking-horizon rule in `app.schemas.request` uses, NOT an
           elapsed-48-hours check (the two are not equivalent — see that
           module's own docstring for why).
        """
        if self.end_at < self.start_at:
            raise ValueError("endAt must not be before startAt")

        now = datetime.now(timezone.utc)
        notice_days = (to_kolkata_date(self.start_at) - to_kolkata_date(now)).days
        if notice_days < MINIMUM_LEAVE_NOTICE_DAYS:
            raise ValueError(
                "startAt must be at least "
                f"{MINIMUM_LEAVE_NOTICE_DAYS} calendar days ahead (Asia/Kolkata)"
            )

        return self


class WorkerLeavePublic(BaseModel):
    """Safe, public view of a `WorkerLeave` belonging to the authenticated worker."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    worker_id: UUID = Field(alias="workerId")
    start_at: datetime = Field(alias="startAt")
    end_at: datetime = Field(alias="endAt")
    status: LeaveStatus
    reviewed_by: UUID | None = Field(alias="reviewedBy")
    reviewed_at: datetime | None = Field(alias="reviewedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WorkerLeaveListResponse(BaseModel):
    """Paginated envelope for `GET /workers/me/leaves`."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkerLeavePublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
