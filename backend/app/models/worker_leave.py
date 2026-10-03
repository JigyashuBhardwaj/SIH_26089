"""
WorkerLeave — Phase 7C-B: the database foundation for worker leave.

This phase is structural ONLY. It introduces the table, the
`LeaveStatus` enum, and the one structural validity constraint
(`end_at >= start_at`). It deliberately does NOT implement any business
rule beyond that: no minimum-duration check, no 2-day notice check, no
annual-quota logic, no overlap check, no approval/rejection endpoint, and
no integration with candidate discovery or `create_assignment`. Those
all belong to later 7C sub-phases, once this foundation exists.

A `WorkerLeave` row starts life as PENDING (the model's own default) and
is later transitioned to APPROVED or REJECTED by an Association Admin —
but the endpoints that perform that transition do not exist yet in this
phase; this model only has to be able to represent the three states.
`CANCELLED` is deliberately NOT a value here — worker-initiated
cancellation of a still-PENDING request was explicitly deferred.

Per the locked Phase 7C investigation, `reviewed_by`/`reviewed_at` mirror
`Assignment.assigned_by`/`responded_at`'s exact shape: a nullable FK to
`accounts.id` (ON DELETE RESTRICT — an association admin's account can't
be deleted out from under a leave decision they made, same reasoning as
`Assignment.assigned_by`) and a nullable timezone-aware timestamp, both
populated only once a PENDING leave is actually reviewed. `created_at`
(from `TimestampMixin`) is this row's submission timestamp — there is no
separate `submitted_at` column, since the existing architecture already
treats `created_at` as exactly that for every other table.

`worker_id` -> `workers.id` is ON DELETE CASCADE, not RESTRICT: unlike
`Assignment` (whose history must never be silently orphaned because other
entities/flows depend on it), a `WorkerLeave` row has no meaning once the
worker it belongs to is gone and nothing else references it — the same
reasoning `WorkerSkill.worker_id` already uses (CASCADE), not the
`Assignment.worker_id`/`Assignment.request_id` reasoning (RESTRICT).

Timezone-aware `DateTime` (not a bare `Date`) for `start_at`/`end_at`,
per the locked investigation recommendation: this is the only choice
consistent with every other time-relevant column in this schema
(`ServiceRequest.requested_date_time`, `Assignment.assigned_at`/
`responded_at`, every `TimestampMixin` column) and avoids introducing the
first calendar-day-vs-timestamp ambiguity anywhere in this codebase —
`ServiceRequest.requested_date_time` is itself a timestamp, so comparing
a leave range against it is a direct, unambiguous timestamp comparison
under this representation (the comparison itself is NOT implemented
here -- that is matching-integration work for a later 7C sub-phase).
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin
from app.models.type_decorators import str_enum_column


class LeaveStatus(str, Enum):
    """
    Per-leave-request status. Locked Phase 7C-B value list: PENDING,
    APPROVED, REJECTED. CANCELLED is deliberately excluded -- worker
    self-cancellation of a still-PENDING request was explicitly deferred
    to a later phase (if it's added at all).
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class WorkerLeave(TimestampMixin, Base):
    __tablename__ = "worker_leaves"
    __table_args__ = (
        # Every query this phase's later sub-phases are already known to
        # need (candidate-discovery's leave-overlap filter,
        # create_assignment's re-check, the worker's own "my leave
        # requests" list, the admin's "pending leave for my association's
        # workers" list) starts from `worker_id`, almost always combined
        # with `status` -- same two-index shape as
        # `ix_assignments_worker_id_status` on the exactly analogous
        # `Assignment` table. The plain `worker_id`-only index is kept
        # alongside it (rather than relying on the composite index's
        # leading column alone) purely to mirror the existing
        # `Assignment` precedent exactly, which keeps both for the same
        # reason.
        Index("ix_worker_leaves_worker_id", "worker_id"),
        Index("ix_worker_leaves_worker_id_status", "worker_id", "status"),
        # Structural validity ONLY -- a leave row must not represent a
        # backwards or zero-width range. This is deliberately NOT the
        # minimum-1-day-duration business rule (that would be
        # `end_at >= start_at + 1 day`, still absent here) -- just basic
        # well-formedness, enforced at the database level the same way
        # `ck_workers_rating_range`/`ck_workers_pincode_six_digits` are.
        CheckConstraint("end_at >= start_at", name="ck_worker_leaves_end_at_after_start_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        str_enum_column(LeaveStatus, name="leave_status"),
        nullable=False,
        default=LeaveStatus.PENDING,
    )
    # Nullable: null until an Association Admin actually reviews this
    # PENDING request. ON DELETE RESTRICT mirrors Assignment.assigned_by
    # exactly -- the admin account that made this decision can't be
    # deleted out from under the historical record of having made it.
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    worker: Mapped["Worker"] = relationship(back_populates="leaves")  # noqa: F821
    # One-directional, no back_populates -- same as
    # `Assignment.assigned_by_account` (Account has no collection of
    # "assignments I made" either, for the identical reason: this is a
    # reference to who reviewed it, not a relationship Account itself
    # needs to navigate).
    reviewed_by_account: Mapped["Account | None"] = relationship()  # noqa: F821
