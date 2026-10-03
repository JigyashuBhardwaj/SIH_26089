"""
Phase 7C-C: pure, reusable business-rule primitives for worker leave.

Locked product decisions this module implements (see the Phase 7C-C
investigation report for the full rationale -- these are approved, final
decisions, not re-derived here):

1. Calendar-day reference timezone: Asia/Kolkata (IST), for EVERY
   calendar-day business rule this codebase has or will have -- leave
   duration, annual quota, cross-year splitting, and (via
   `to_kolkata_date`, imported from here) the Phase 5E-C service-request
   maximum booking horizon in `app/schemas/request.py`. Database
   timestamps remain timezone-aware exactly as they already are
   (TIMESTAMPTZ, normally stored/compared in UTC); only the *business-rule*
   day boundary is Asia/Kolkata -- never the machine's local timezone
   (which this module never consults) and never naive UTC midnight.

2. Leave intervals are INCLUSIVE at both ends:
   - Day-count: 10 Oct -> 10 Oct is 1 day; 10 Oct -> 12 Oct is 3 days.
   - Overlap: two ranges overlap iff
         existing.start_at <= candidate.end_at
         AND existing.end_at >= candidate.start_at
     so 10-12 Oct and 12-14 Oct DO overlap (they share 12 Oct).

Scope of this phase (7C-C): ONLY the pure/reusable primitives a future
worker-leave-submission endpoint and a future association-admin
leave-approval endpoint will both need. This phase deliberately does NOT
implement:
  - any API route (no leave submission/approval/list endpoint exists yet)
  - any ownership/authorization check (those belong to the route that
    calls these primitives, exactly like every existing router's own
    `_get_own_worker`/`_require_own_association_id` helpers)
  - the approval-time row-locking strategy (`SELECT ... FOR UPDATE`) a
    real approval endpoint must add on top of
    `approved_leave_days_in_year`/`leave_overlaps_existing` below to close
    the concurrent-approval race the investigation report describes --
    that belongs to the endpoint performing the write, not to these
    read-only helpers
  - any change to candidate discovery, `create_assignment`, or matching
    (Phase 7C-F's job)

No PostgreSQL range type, EXCLUDE constraint, or other database-level
overlap enforcement is introduced here, consistent with the rest of this
schema -- see `app.models.worker_leave`'s own docstring for why.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.enums import AssignmentStatus
from app.models.service_request import ServiceRequest
from app.models.worker_leave import LeaveStatus, WorkerLeave

# The single authoritative timezone for every calendar-day business rule
# in this codebase -- never the machine's local timezone (which this
# sandbox/production host is not guaranteed to have set to IST) and never
# naive UTC-midnight, which would silently misclassify any leave or
# booking request made in the IST evening (UTC mornings/afternoons).
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

# Rule 4 (locked product decision): 60 approved calendar days per
# calendar year. This constant is exported so the future approval
# endpoint compares against the same value this module's own tests use --
# never a magic number re-typed at the call site.
MAX_ANNUAL_LEAVE_DAYS = 60

# Rule 5 (locked product decision): only a PENDING or APPROVED leave can
# block another leave from overlapping it. REJECTED never blocks -- an
# admin has already decided it doesn't stand, so it has no more claim on
# the calendar than a leave that was never submitted.
_BLOCKING_LEAVE_STATUSES = (LeaveStatus.PENDING, LeaveStatus.APPROVED)

# Rule 6 (locked product decision): "approved leave cannot conflict with
# an existing ACCEPTED assignment" -- only ACCEPTED represents a worker
# actually committed to performing a job. PENDING_RESPONSE is still just
# an unaccepted offer (mirrors `app/api/associations.py`'s own
# `_ACTIVE_ASSIGNMENT_STATUSES` reasoning, narrowed further here per this
# rule's own explicit wording, which names ACCEPTED only -- not also
# PENDING_RESPONSE the way that other tuple does). DECLINED,
# CANCELLED_BY_WORKER, and COMPLETED are all resolved/historical and
# never conflict.
_COMMITTED_ASSIGNMENT_STATUSES = (AssignmentStatus.ACCEPTED,)


def to_kolkata_date(value: datetime) -> date:
    """
    The Asia/Kolkata calendar date a timezone-aware timestamp falls on.

    This is the single shared definition of "calendar day" for every
    business rule in this codebase that needs one -- Phase 7C-C's leave
    rules below, and the Phase 5E-C service-request maximum booking
    horizon in `app/schemas/request.py`, which imports this function
    directly rather than re-deriving its own notion of "calendar day".

    `value` must be timezone-aware; a naive datetime is rejected outright
    rather than silently assumed to already be in some timezone,
    mirroring `ServiceRequestCreate._validate_requested_date_time`'s own
    naive-datetime rejection.
    """
    if value.tzinfo is None:
        raise ValueError("to_kolkata_date requires a timezone-aware datetime")
    return value.astimezone(KOLKATA_TZ).date()


def leave_day_count(start_at: datetime, end_at: datetime) -> int:
    """
    Rule 3 (minimum leave duration) / Rule 4 (annual quota) primitive:
    the number of Asia/Kolkata calendar days a leave spans, INCLUSIVE of
    both endpoints -- 10 Oct -> 10 Oct is 1 day, 10 Oct -> 12 Oct is 3
    days.

    Does not itself validate `end_at >= start_at` -- that structural
    invariant is already enforced at the database level by
    `ck_worker_leaves_end_at_after_start_at` on every persisted
    `WorkerLeave` row, so every caller passing persisted values already
    has that guarantee.
    """
    start_date = to_kolkata_date(start_at)
    end_date = to_kolkata_date(end_at)
    return (end_date - start_date).days + 1


def split_leave_days_by_year(start_at: datetime, end_at: datetime) -> dict[int, int]:
    """
    Rule 4 (annual quota, cross-year splitting): the number of
    Asia/Kolkata calendar days this leave spans in EACH calendar year it
    touches -- e.g. 30 Dec -> 2 Jan splits as `{2026: 2, 2027: 2}`.

    Walks the inclusive Asia/Kolkata date range day by day. Leave spans
    are always small in practice (bounded by the 60-day annual quota
    itself), so this is never a performance concern, and a direct loop is
    far easier to verify correct at the year boundary than a closed-form
    formula would be.
    """
    start_date = to_kolkata_date(start_at)
    end_date = to_kolkata_date(end_at)

    counts: dict[int, int] = {}
    one_day = timedelta(days=1)
    current = start_date
    while current <= end_date:
        counts[current.year] = counts.get(current.year, 0) + 1
        current += one_day
    return counts


def approved_leave_days_in_year(
    db: Session,
    worker_id: UUID,
    year: int,
    *,
    exclude_leave_id: UUID | None = None,
) -> int:
    """
    Rule 4: total Asia/Kolkata calendar days of APPROVED leave this
    worker already has in `year`, summed across every APPROVED
    `WorkerLeave` row that touches that year (via
    `split_leave_days_by_year`, so a leave crossing into/out of `year`
    contributes only the days that actually fall within it). PENDING and
    REJECTED rows are excluded entirely from the query itself -- only
    APPROVED leave consumes quota, per the locked product rule.

    `exclude_leave_id` lets a future approval endpoint ask "what would
    this worker's total be without counting the very row I'm about to
    approve" -- this function performs no cap comparison itself (see
    `MAX_ANNUAL_LEAVE_DAYS`); it only computes the current total.

    Does not lock any row. A future approval endpoint must acquire its
    own `SELECT ... FOR UPDATE` before calling this, as part of closing
    the concurrent-approval race described in the Phase 7C-C
    investigation report -- that locking strategy belongs to the
    endpoint performing the write, not to this read-only helper.
    """
    query = select(WorkerLeave).where(
        WorkerLeave.worker_id == worker_id,
        WorkerLeave.status == LeaveStatus.APPROVED,
    )
    if exclude_leave_id is not None:
        query = query.where(WorkerLeave.id != exclude_leave_id)

    approved_leaves = db.execute(query).scalars().all()

    total = 0
    for leave in approved_leaves:
        total += split_leave_days_by_year(leave.start_at, leave.end_at).get(year, 0)
    return total


def leave_overlaps_existing(
    db: Session,
    worker_id: UUID,
    start_at: datetime,
    end_at: datetime,
    *,
    exclude_leave_id: UUID | None = None,
) -> bool:
    """
    Rule 5: whether this worker already has a PENDING or APPROVED
    `WorkerLeave` row whose interval overlaps `[start_at, end_at]`.
    REJECTED rows never block, per the locked product rule.

    Inclusive overlap semantics, per the locked product decision:

        existing.start_at <= end_at AND existing.end_at >= start_at

    so a leave ending exactly when another begins (10-12 Oct and 12-14
    Oct) DOES overlap -- they share 12 Oct.

    `exclude_leave_id` excludes one specific persisted row from the
    check -- the row being approved itself, when a future admin-approval
    endpoint re-runs this check at approval time (it must not treat the
    leave it is about to approve as conflicting with itself).
    """
    query = select(WorkerLeave.id).where(
        WorkerLeave.worker_id == worker_id,
        WorkerLeave.status.in_(_BLOCKING_LEAVE_STATUSES),
        WorkerLeave.start_at <= end_at,
        WorkerLeave.end_at >= start_at,
    )
    if exclude_leave_id is not None:
        query = query.where(WorkerLeave.id != exclude_leave_id)

    return db.execute(query.limit(1)).scalar_one_or_none() is not None


def leave_conflicts_accepted_assignment(
    db: Session, worker_id: UUID, start_at: datetime, end_at: datetime
) -> bool:
    """
    Rule 6: whether this worker has an ACCEPTED `Assignment` whose
    `ServiceRequest.requested_date_time` falls INCLUSIVELY within
    `[start_at, end_at]`. PENDING_RESPONSE (an unaccepted offer),
    DECLINED, CANCELLED_BY_WORKER, and COMPLETED never conflict -- see
    `_COMMITTED_ASSIGNMENT_STATUSES` above for why only ACCEPTED counts.

    Per the locked product rule, this must be checked both when a leave
    is submitted and again when it is approved (an assignment can be
    accepted in the gap between the two). This function only answers the
    question for a single point in time; a future endpoint decides when
    to call it and what row-locking, if any, surrounds that call.
    """
    conflicting_assignment = db.execute(
        select(Assignment.id)
        .join(ServiceRequest, Assignment.request_id == ServiceRequest.id)
        .where(
            Assignment.worker_id == worker_id,
            Assignment.status.in_(_COMMITTED_ASSIGNMENT_STATUSES),
            ServiceRequest.requested_date_time >= start_at,
            ServiceRequest.requested_date_time <= end_at,
        )
        .limit(1)
    ).scalar_one_or_none()
    return conflicting_assignment is not None
