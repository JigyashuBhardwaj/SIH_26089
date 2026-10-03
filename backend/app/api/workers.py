"""
Phase 5E-D: WORKER read-only routes over their own profile and assignment
history.

`GET /workers/me`              — the authenticated worker's own Worker profile.
`GET /workers/me/assignments`  — the authenticated worker's own Assignment history.

Identity is always derived from the authenticated Account -> its own
`Worker` row, never from a client-supplied id. READ-ONLY: no assignment
creation, response (accept/decline), or status mutation happens here.

Phase 6E-A enriches `GET /workers/me/assignments` with a small
`requestSummary` per item (`app.schemas.assignment.WorkerAssignmentPublic`)
so the Worker app can show real job information (service, requested
date/time, address) instead of a synthetic placeholder — see that
schema's own docstring for why this is a separate response type from the
plain `AssignmentPublic` every other Assignment-returning route still
uses unchanged.

Phase 7C-D adds the worker's own leave-submission/history routes:

`POST /workers/me/leaves` — submit a new leave request, always starting
    at PENDING. Enforces only the schema-level rules in
    `app.schemas.worker_leave.WorkerLeaveCreate` (naive-datetime
    rejection, invalid interval, 2-Asia/Kolkata-calendar-day minimum
    notice) plus the two database-backed checks that need a session
    (overlap with an existing PENDING/APPROVED leave, conflict with an
    existing ACCEPTED assignment) via the existing
    `app.domain.leave_rules` primitives from Phase 7C-C. Does NOT check
    the annual 60-day quota (an approval-time gate, Phase 7C-E) and does
    NOT implement approval/rejection (also Phase 7C-E).
`GET /workers/me/leaves`  — the authenticated worker's own leave history,
    every status included, no filtering.

Neither route touches candidate discovery, `create_assignment`, or any
matching logic (Phase 7C-F's job).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.errors import conflict, not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.domain.leave_rules import leave_conflicts_accepted_assignment, leave_overlaps_existing
from app.models.account import Account
from app.models.assignment import Assignment
from app.models.enums import AccountRole
from app.models.service_request import ServiceRequest
from app.models.worker import Worker
from app.models.worker_leave import LeaveStatus, WorkerLeave
from app.schemas.assignment import (
    AssignmentRequestSummary,
    WorkerAssignmentListResponse,
    WorkerAssignmentPublic,
)
from app.schemas.pagination import PaginationParams
from app.schemas.worker import WorkerPublic
from app.schemas.worker_leave import WorkerLeaveCreate, WorkerLeaveListResponse, WorkerLeavePublic

router = APIRouter(prefix="/workers", tags=["workers"])


def _get_own_worker(db: Session, account: Account) -> Worker:
    """
    Resolve the authenticated Account's own Worker row. 404 if the
    authenticated WORKER account has no linked Worker profile.
    """
    worker = db.execute(
        select(Worker).where(Worker.account_id == account.id)
    ).scalar_one_or_none()
    if worker is None:
        raise not_found("No worker profile is linked to this account")
    return worker


@router.get("/me", response_model=WorkerPublic)
def get_own_worker_profile(
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> WorkerPublic:
    """Return the authenticated worker's own Worker profile."""
    worker = _get_own_worker(db, account)
    return WorkerPublic.model_validate(worker)


@router.get("/me/assignments", response_model=WorkerAssignmentListResponse)
def list_own_assignments(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> WorkerAssignmentListResponse:
    """
    List only the authenticated worker's own Assignment history (no
    "active only" filter), ordered by `assigned_at DESC` with `id DESC`
    as a stable tiebreaker.

    Phase 6E-A: each item also carries `requestSummary`, joined here
    (`Assignment.request` -> `ServiceRequest.service`) in the same query
    that fetches the page of assignments, rather than one extra query per
    row.
    """
    worker = _get_own_worker(db, account)

    base_query = select(Assignment).where(Assignment.worker_id == worker.id)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    assignments = (
        db.execute(
            base_query.options(
                joinedload(Assignment.request).joinedload(ServiceRequest.service)
            )
            .order_by(Assignment.assigned_at.desc(), Assignment.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    items: list[WorkerAssignmentPublic] = []
    for assignment in assignments:
        item = WorkerAssignmentPublic.model_validate(assignment)
        item.request_summary = AssignmentRequestSummary(
            request_code=assignment.request.request_code,
            service_name=assignment.request.service.name,
            requested_date_time=assignment.request.requested_date_time,
            address=assignment.request.address,
            pincode=assignment.request.pincode,
        )
        items.append(item)

    return WorkerAssignmentListResponse(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.post("/me/leaves", response_model=WorkerLeavePublic, status_code=201)
def submit_own_leave(
    payload: WorkerLeaveCreate,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> WorkerLeavePublic:
    """
    The authenticated worker submits a new leave request for themselves,
    always starting at PENDING (Phase 7C-D). `workerId` is never accepted
    from the client -- it is always the authenticated worker's own id,
    resolved via `_get_own_worker` below.

    `WorkerLeaveCreate` already enforces, at the schema level (422 on
    failure): naive-datetime rejection on both fields, `endAt >= startAt`
    (the "invalid interval" case), and the 2-Asia/Kolkata-calendar-day
    minimum notice period. The two checks below need a database session
    and so cannot live in the schema:

      1. `leave_overlaps_existing` -- this worker must not already have a
         PENDING or APPROVED leave whose interval overlaps this one
         (REJECTED leave never blocks). 409 if it does.
      2. `leave_conflicts_accepted_assignment` -- this worker must not
         have an ACCEPTED Assignment whose ServiceRequest falls within
         this leave's range. 409 if it does.

    Does NOT check the annual 60-day quota (Phase 7C-C's
    `approved_leave_days_in_year` is intentionally not called here) --
    only APPROVED leave consumes quota, and quota is an approval-time
    gate (Phase 7C-E), not a submission-time one. Does NOT implement
    approval/rejection, and never transitions this row past PENDING.

    Needs no row lock: this inserts a brand-new row that doesn't exist
    yet to lock, exactly like `create_request` in `app/api/requests.py`
    inserts a new ServiceRequest with no `with_for_update()` anywhere in
    that route -- there is no already-existing row being read-then-
    written here for a lock to protect.
    """
    worker = _get_own_worker(db, account)

    if leave_overlaps_existing(db, worker.id, payload.start_at, payload.end_at):
        raise conflict("This leave request overlaps an existing pending or approved leave")

    if leave_conflicts_accepted_assignment(db, worker.id, payload.start_at, payload.end_at):
        raise conflict("This leave request conflicts with an existing accepted assignment")

    leave = WorkerLeave(
        worker_id=worker.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=LeaveStatus.PENDING,
    )
    db.add(leave)
    db.flush()
    db.refresh(leave)

    return WorkerLeavePublic.model_validate(leave)


@router.get("/me/leaves", response_model=WorkerLeaveListResponse)
def list_own_leaves(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> WorkerLeaveListResponse:
    """
    List only the authenticated worker's own `WorkerLeave` history (every
    status included, no filtering), ordered by `created_at DESC` with
    `id DESC` as a stable tiebreaker -- the same ordering convention as
    `list_own_assignments`/`app.api.requests.list_own_requests`.
    """
    worker = _get_own_worker(db, account)

    base_query = select(WorkerLeave).where(WorkerLeave.worker_id == worker.id)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    leaves = (
        db.execute(
            base_query.order_by(WorkerLeave.created_at.desc(), WorkerLeave.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    return WorkerLeaveListResponse(
        items=[WorkerLeavePublic.model_validate(leave) for leave in leaves],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )
