"""
Phase 5E-F-A: WORKER lifecycle mutations for a Worker's own Assignment
offers.

`POST /assignments/{assignment_id}/accept`   — PENDING_RESPONSE -> ACCEPTED
`POST /assignments/{assignment_id}/decline`  — PENDING_RESPONSE -> DECLINED
`POST /assignments/{assignment_id}/cancel`   — ACCEPTED -> CANCELLED_BY_WORKER

Phase 5E-I adds the one remaining Assignment-side lifecycle mutation:

`POST /assignments/{assignment_id}/complete` — ACCEPTED -> COMPLETED

This router never creates an Assignment itself -- that remains the
Phase 5E-E Association Admin endpoint's job
(`POST /associations/me/requests/{request_id}/assignments`). It only
transitions an Assignment that already exists to a resolved state, always
together with the matching ServiceRequest transition:

    Accept:   Assignment PENDING_RESPONSE -> ACCEPTED,           ServiceRequest ASSIGNED -> ACCEPTED
    Decline:  Assignment PENDING_RESPONSE -> DECLINED,           ServiceRequest ASSIGNED -> MATCHING
    Cancel:   Assignment ACCEPTED         -> CANCELLED_BY_WORKER, ServiceRequest ACCEPTED -> MATCHING
    Complete: Assignment ACCEPTED         -> COMPLETED,           ServiceRequest ACCEPTED -> WORKER_COMPLETED

Assignment rows are never deleted or overwritten -- a decline/cancel/
complete leaves the acted-upon row as a permanent historical record, and
a new Assignment (via the Phase 5E-E endpoint) is the only way a request
gets re-offered to another worker. COMPLETED is terminal for an
Assignment: once reached, no further worker action here targets that row
again. What happens to the ServiceRequest after WORKER_COMPLETED (user
confirmation, demo payment) is handled entirely by
`app/api/requests.py`, which never touches the Assignment table.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import conflict, not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.assignment import Assignment
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus
from app.models.service_request import ServiceRequest
from app.models.worker import Worker
from app.schemas.assignment import AssignmentPublic

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _get_own_worker(db: Session, account: Account) -> Worker:
    """Resolve the authenticated Account's own Worker row. 404 if none is linked."""
    worker = db.execute(
        select(Worker).where(Worker.account_id == account.id)
    ).scalar_one_or_none()
    if worker is None:
        raise not_found("No worker profile is linked to this account")
    return worker


def _lock_assignment_and_request(
    db: Session, assignment_id: UUID
) -> tuple[Assignment, ServiceRequest]:
    """
    Lock (`SELECT ... FOR UPDATE`) the Assignment row, then its
    associated ServiceRequest row, in that fixed order.

    Every lifecycle mutation in this router acquires locks in this same
    Assignment-then-ServiceRequest order, so two concurrent mutations
    targeting the same assignment_id always serialize on the Assignment
    row lock alone (acquired first, before either transaction reads or
    writes anything else) -- the second transaction blocks until the
    first's flush/rollback completes, then re-reads the now-current
    Assignment/ServiceRequest state under its own lock, so it correctly
    observes whatever the first transaction did and is rejected with 409
    rather than racing to also apply a transition.
    """
    assignment = db.execute(
        select(Assignment).where(Assignment.id == assignment_id).with_for_update()
    ).scalar_one_or_none()
    if assignment is None:
        raise not_found("Assignment not found")

    # The FK (Assignment.request_id -> service_requests.id, ON DELETE
    # RESTRICT) guarantees this always resolves.
    service_request = db.execute(
        select(ServiceRequest).where(ServiceRequest.id == assignment.request_id).with_for_update()
    ).scalar_one()

    return assignment, service_request


@router.post("/{assignment_id}/accept", response_model=AssignmentPublic)
def accept_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> AssignmentPublic:
    """
    The authenticated worker accepts their own PENDING_RESPONSE
    Assignment. Requires the linked ServiceRequest to still be ASSIGNED.
    Transitions both atomically: Assignment -> ACCEPTED, ServiceRequest
    -> ACCEPTED.
    """
    worker = _get_own_worker(db, account)
    assignment, service_request = _lock_assignment_and_request(db, assignment_id)

    # An Assignment that exists but belongs to another worker is
    # indistinguishable from a nonexistent one.
    if assignment.worker_id != worker.id:
        raise not_found("Assignment not found")

    if assignment.status != AssignmentStatus.PENDING_RESPONSE:
        raise conflict("Assignment is not awaiting a response")
    if service_request.status != ServiceRequestStatus.ASSIGNED:
        raise conflict("Service request is not in a state that can be accepted")

    assignment.status = AssignmentStatus.ACCEPTED
    assignment.responded_at = datetime.now(timezone.utc)
    service_request.status = ServiceRequestStatus.ACCEPTED

    db.flush()
    db.refresh(assignment)

    return AssignmentPublic.model_validate(assignment)


@router.post("/{assignment_id}/decline", response_model=AssignmentPublic)
def decline_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> AssignmentPublic:
    """
    The authenticated worker declines their own PENDING_RESPONSE
    Assignment. Requires the linked ServiceRequest to still be ASSIGNED.
    Transitions both atomically: Assignment -> DECLINED, ServiceRequest
    -> MATCHING. The Assignment row is never deleted or reused -- a new
    Assignment (via the Phase 5E-E endpoint) is the only way to re-offer
    the request to another worker.
    """
    worker = _get_own_worker(db, account)
    assignment, service_request = _lock_assignment_and_request(db, assignment_id)

    if assignment.worker_id != worker.id:
        raise not_found("Assignment not found")

    if assignment.status != AssignmentStatus.PENDING_RESPONSE:
        raise conflict("Assignment is not awaiting a response")
    if service_request.status != ServiceRequestStatus.ASSIGNED:
        raise conflict("Service request is not in a state that can be declined")

    assignment.status = AssignmentStatus.DECLINED
    assignment.responded_at = datetime.now(timezone.utc)
    service_request.status = ServiceRequestStatus.MATCHING

    db.flush()
    db.refresh(assignment)

    return AssignmentPublic.model_validate(assignment)


@router.post("/{assignment_id}/cancel", response_model=AssignmentPublic)
def cancel_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> AssignmentPublic:
    """
    The authenticated worker cancels their own previously-ACCEPTED
    Assignment (they can no longer perform the work). Requires the
    linked ServiceRequest to still be ACCEPTED. Transitions both
    atomically: Assignment -> CANCELLED_BY_WORKER, ServiceRequest ->
    MATCHING. A still-PENDING_RESPONSE Assignment cannot be cancelled
    (that is what decline is for) -- only an already-accepted one.
    `responded_at` is left untouched here (it already records the
    original accept time from `accept_assignment` above).
    """
    worker = _get_own_worker(db, account)
    assignment, service_request = _lock_assignment_and_request(db, assignment_id)

    if assignment.worker_id != worker.id:
        raise not_found("Assignment not found")

    if assignment.status != AssignmentStatus.ACCEPTED:
        raise conflict("Assignment is not currently accepted")
    if service_request.status != ServiceRequestStatus.ACCEPTED:
        raise conflict("Service request is not in a state that can be cancelled")

    assignment.status = AssignmentStatus.CANCELLED_BY_WORKER
    service_request.status = ServiceRequestStatus.MATCHING

    db.flush()
    db.refresh(assignment)

    return AssignmentPublic.model_validate(assignment)


@router.post("/{assignment_id}/complete", response_model=AssignmentPublic)
def complete_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> AssignmentPublic:
    """
    The authenticated worker marks their own ACCEPTED Assignment as the
    completed job (Phase 5E-I). Requires the linked ServiceRequest to
    still be ACCEPTED. Transitions both atomically: Assignment ->
    COMPLETED, ServiceRequest -> WORKER_COMPLETED. No new Assignment is
    created, and this row's history (including its original
    `responded_at` from `accept_assignment`) is left untouched --
    `updated_at` still advances automatically via the model's own
    `onupdate=func.now()`. COMPLETED is terminal for this Assignment: a
    second call against the same row is rejected with 409, exactly like
    every other lifecycle mutation on this router. What happens next to
    the ServiceRequest (user confirmation, demo payment) is entirely
    `app/api/requests.py`'s responsibility -- this endpoint never reads
    or writes past WORKER_COMPLETED.
    """
    worker = _get_own_worker(db, account)
    assignment, service_request = _lock_assignment_and_request(db, assignment_id)

    # An Assignment that exists but belongs to another worker is
    # indistinguishable from a nonexistent one.
    if assignment.worker_id != worker.id:
        raise not_found("Assignment not found")

    if assignment.status != AssignmentStatus.ACCEPTED:
        raise conflict("Assignment is not currently accepted")
    if service_request.status != ServiceRequestStatus.ACCEPTED:
        raise conflict("Service request is not in a state that can be completed")

    assignment.status = AssignmentStatus.COMPLETED
    service_request.status = ServiceRequestStatus.WORKER_COMPLETED

    db.flush()
    db.refresh(assignment)

    return AssignmentPublic.model_validate(assignment)
