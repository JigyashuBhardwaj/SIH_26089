"""
Phase 5E-C: the authenticated USER's own `ServiceRequest` routes.

`POST /requests`             — create a new request for the authenticated USER.
`GET /requests`               — list only the authenticated USER's own requests.
`GET /requests/{request_id}`  — retrieve a single request, only if it
                                 belongs to the authenticated USER.

Locked scope for this phase: creation only ever produces a request in
`PENDING` status — no matching, no `Assignment` row, no lifecycle
transitions. Identity is always derived from the authenticated Account ->
its own `UserProfile`, never from a client-supplied id — there is no
`user_id` parameter anywhere on this router.

Phase 5E-I adds the two remaining USER-side lifecycle mutations, closing
out the request lifecycle once the worker has done their part
(`app/api/assignments.py`'s `complete_assignment` moves a request to
WORKER_COMPLETED):

`POST /requests/{request_id}/confirm` — WORKER_COMPLETED -> USER_CONFIRMED -> PAYMENT_PENDING
`POST /requests/{request_id}/pay`     — PAYMENT_PENDING -> PAID -> COMPLETED

Both are single user actions that each persist only their own final
status in one atomic flush — USER_CONFIRMED and PAID remain canonical
`ServiceRequestStatus` values that the request conceptually passes
through, exactly as the locked Phase 5E-I spec allows, but neither is
ever the row's own persisted end-of-request state here. Neither route
reads or writes the `Assignment` table at all — Assignment history is
untouched by both. `pay` is a demo/MVP action only: there is no Payment
model/table and no real payment gateway integration anywhere in this
codebase.

Phase 5E-J adds the one remaining USER-side mutation, user-initiated
cancellation:

`POST /requests/{request_id}/cancel` — {PENDING, MATCHING, ASSIGNED, ACCEPTED} -> CANCELLED_BY_USER

Any other starting status (WORKER_COMPLETED, USER_CONFIRMED,
PAYMENT_PENDING, PAID, COMPLETED, or an already-CANCELLED_BY_USER
request) is rejected with 409 — cancellation is only meaningful before
the worker has finished the job. Like `confirm`/`pay`, this route never
reads or writes the `Assignment` table: a cancelled request's Assignment
history (including a currently-ACCEPTED row, if one exists) is left
completely untouched — no status change, no new row, no reassignment.
CANCELLED_BY_USER is a `ServiceRequestStatus` value only; it is
deliberately distinct from `AssignmentStatus.CANCELLED_BY_WORKER`
(worker-initiated, handled entirely by `app/api/assignments.py`) and no
new `AssignmentStatus` value is introduced here.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import conflict, not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.assignment import Assignment
from app.models.association import Association
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus
from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.user_profile import UserProfile
from app.models.worker import Worker
from app.schemas.pagination import PaginationParams
from app.schemas.request import (
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestPublic,
)

router = APIRouter(prefix="/requests", tags=["requests"])

# Phase 6E-A: an Assignment counts as the request's "currently relevant"
# one for surfacing assigned-worker info to the USER only once a worker
# has actually accepted -- ACCEPTED (job in progress) or COMPLETED (job
# done, worker info still relevant through confirmation/payment).
# Deliberately excludes PENDING_RESPONSE (offered but not yet accepted —
# nothing to show the user yet) and DECLINED/CANCELLED_BY_WORKER
# (superseded, never the "current" worker). Business rules elsewhere
# guarantee at most one Assignment per request is ever in one of these
# two statuses at a time, so this never needs to pick among several.
_CURRENT_ASSIGNMENT_STATUSES = (AssignmentStatus.ACCEPTED, AssignmentStatus.COMPLETED)


def _resolve_current_assignment_worker(db: Session, request_id: UUID) -> Worker | None:
    """Single-request lookup of the currently relevant assigned Worker, or None."""
    return db.execute(
        select(Worker)
        .join(Assignment, Assignment.worker_id == Worker.id)
        .where(
            Assignment.request_id == request_id,
            Assignment.status.in_(_CURRENT_ASSIGNMENT_STATUSES),
        )
        .order_by(Assignment.assigned_at.desc(), Assignment.id.desc())
        .limit(1)
    ).scalars().first()


def _attach_current_assignment_workers(
    db: Session, service_requests: list[ServiceRequest]
) -> dict[UUID, Worker]:
    """
    Batch version of `_resolve_current_assignment_worker` for a list
    result (`list_own_requests`) -- one query for the whole page rather
    than one per row.
    """
    if not service_requests:
        return {}
    request_ids = [service_request.id for service_request in service_requests]
    rows = db.execute(
        select(Assignment.request_id, Worker)
        .join(Worker, Worker.id == Assignment.worker_id)
        .where(
            Assignment.request_id.in_(request_ids),
            Assignment.status.in_(_CURRENT_ASSIGNMENT_STATUSES),
        )
    ).all()
    return {request_id: worker for request_id, worker in rows}


def _build_service_request_public(
    service_request: ServiceRequest, worker: Worker | None
) -> ServiceRequestPublic:
    """Build a `ServiceRequestPublic`, attaching assigned-worker info if `worker` is given."""
    public = ServiceRequestPublic.model_validate(service_request)
    if worker is not None:
        public.assigned_worker_id = worker.id
        public.assigned_worker_name = worker.full_name
        public.assigned_worker_phone = worker.phone
    return public


def _get_own_user_profile(db: Session, account: Account) -> UserProfile:
    """
    Resolve the authenticated Account's own UserProfile — the only path
    from a Bearer token to a `ServiceRequest.user_id` value. 404 if the
    authenticated USER has no linked profile.
    """
    profile = db.execute(
        select(UserProfile).where(UserProfile.account_id == account.id)
    ).scalar_one_or_none()
    if profile is None:
        raise not_found("No user profile is linked to this account")
    return profile


@router.post("", response_model=ServiceRequestPublic, status_code=201)
def create_request(
    payload: ServiceRequestCreate,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> ServiceRequestPublic:
    """
    Create exactly one `ServiceRequest`, always starting at `PENDING`.
    `serviceId` must reference an existing, active `Service`; `associationId`
    must reference an existing `Association`. Either failing raises 404
    (an inactive service behaves the same as a nonexistent one, per the
    existing `GET /services/{service_id}` convention).
    """
    profile = _get_own_user_profile(db, account)

    service = db.execute(
        select(Service).where(
            Service.id == payload.service_id, Service.is_active.is_(True)
        )
    ).scalar_one_or_none()
    if service is None:
        raise not_found("Service not found")

    association = db.get(Association, payload.association_id)
    if association is None:
        raise not_found("Association not found")

    service_request = ServiceRequest(
        user_id=profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=payload.requested_date_time,
        address=payload.address,
        pincode=payload.pincode,
        status=ServiceRequestStatus.PENDING,
    )
    db.add(service_request)
    db.flush()
    db.refresh(service_request)

    return ServiceRequestPublic.model_validate(service_request)


@router.get("", response_model=ServiceRequestListResponse)
def list_own_requests(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> ServiceRequestListResponse:
    """
    List only the authenticated USER's own requests, newest first
    (`created_at DESC`, with `id DESC` as a stable tiebreaker for
    otherwise-equal timestamps).
    """
    profile = _get_own_user_profile(db, account)

    base_query = select(ServiceRequest).where(ServiceRequest.user_id == profile.id)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    service_requests = (
        db.execute(
            base_query.order_by(
                ServiceRequest.created_at.desc(), ServiceRequest.id.desc()
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    workers_by_request_id = _attach_current_assignment_workers(db, service_requests)

    return ServiceRequestListResponse(
        items=[
            _build_service_request_public(
                service_request, workers_by_request_id.get(service_request.id)
            )
            for service_request in service_requests
        ],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/{request_id}", response_model=ServiceRequestPublic)
def get_own_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> ServiceRequestPublic:
    """
    Return a single request, only if it belongs to the authenticated
    USER's own profile. A nonexistent request and another user's request
    both return 404 — a client cannot tell the two apart.
    """
    profile = _get_own_user_profile(db, account)

    service_request = db.execute(
        select(ServiceRequest).where(
            ServiceRequest.id == request_id, ServiceRequest.user_id == profile.id
        )
    ).scalar_one_or_none()

    if service_request is None:
        raise not_found("Service request not found")

    worker = _resolve_current_assignment_worker(db, service_request.id)
    return _build_service_request_public(service_request, worker)


def _lock_own_request(db: Session, profile: UserProfile, request_id: UUID) -> ServiceRequest:
    """
    Lock (`SELECT ... FOR UPDATE`) the ServiceRequest row as the very
    first step, before any state is read — the same order every other
    lifecycle mutation in this codebase uses
    (`app/api/associations.py`'s `create_assignment`,
    `app/api/assignments.py`'s `_lock_assignment_and_request`) — then
    verify it belongs to the authenticated USER's own profile. A
    nonexistent request and one belonging to another user are
    indistinguishable (both 404).
    """
    service_request = db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
    ).scalar_one_or_none()
    if service_request is None or service_request.user_id != profile.id:
        raise not_found("Service request not found")
    return service_request


@router.post("/{request_id}/confirm", response_model=ServiceRequestPublic)
def confirm_request_completion(
    request_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> ServiceRequestPublic:
    """
    The authenticated user confirms that the worker's completed job is
    done (Phase 5E-I). Requires the request to currently be
    WORKER_COMPLETED. This one action conceptually passes the request
    through USER_CONFIRMED — still a canonical `ServiceRequestStatus`
    value — but finishes at PAYMENT_PENDING in a single atomic
    transaction/flush, matching how every other lifecycle mutation on
    this codebase's routes (accept/decline/cancel/complete) persists
    only its own resulting status per action. Never reads or writes the
    Assignment table — Assignment history is untouched by this route.
    """
    profile = _get_own_user_profile(db, account)
    service_request = _lock_own_request(db, profile, request_id)

    if service_request.status != ServiceRequestStatus.WORKER_COMPLETED:
        raise conflict("Service request is not awaiting user confirmation")

    service_request.status = ServiceRequestStatus.PAYMENT_PENDING

    db.flush()
    db.refresh(service_request)

    return ServiceRequestPublic.model_validate(service_request)


@router.post("/{request_id}/pay", response_model=ServiceRequestPublic)
def pay_for_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> ServiceRequestPublic:
    """
    Demo/MVP payment completion ONLY (Phase 5E-I) — there is no real
    payment gateway integration, no Payment model/table, and no external
    provider of any kind anywhere in this codebase. This models the user
    pressing "Done" on a future demo payment screen. Requires the request
    to currently be PAYMENT_PENDING. This one action conceptually passes
    the request through PAID — still a canonical `ServiceRequestStatus`
    value — but finishes at COMPLETED in a single atomic
    transaction/flush. Never reads or writes the Assignment table —
    Assignment history is untouched by this route.
    """
    profile = _get_own_user_profile(db, account)
    service_request = _lock_own_request(db, profile, request_id)

    if service_request.status != ServiceRequestStatus.PAYMENT_PENDING:
        raise conflict("Service request is not awaiting payment")

    service_request.status = ServiceRequestStatus.COMPLETED

    db.flush()
    db.refresh(service_request)

    return ServiceRequestPublic.model_validate(service_request)


# ServiceRequest statuses from which the owning USER may still cancel.
# Anything else (WORKER_COMPLETED onward, or an already-cancelled
# request) means the job is too far along for the user to unilaterally
# call it off, and is rejected with 409.
_USER_CANCELLABLE_STATUSES = (
    ServiceRequestStatus.PENDING,
    ServiceRequestStatus.MATCHING,
    ServiceRequestStatus.ASSIGNED,
    ServiceRequestStatus.ACCEPTED,
)


@router.post("/{request_id}/cancel", response_model=ServiceRequestPublic)
def cancel_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> ServiceRequestPublic:
    """
    The authenticated user cancels their own ServiceRequest (Phase
    5E-J). Allowed only from PENDING, MATCHING, ASSIGNED, or ACCEPTED —
    any later status (WORKER_COMPLETED, USER_CONFIRMED, PAYMENT_PENDING,
    PAID, COMPLETED) or an already-CANCELLED_BY_USER request is rejected
    with 409, since the job is either already finished or already
    cancelled.

    This route never reads or writes the `Assignment` table at all.
    Whatever Assignment history exists for this request — including a
    currently-ACCEPTED row, if the request was ACCEPTED — is left
    completely untouched: no status change, no new Assignment, no
    automatic reassignment. `CANCELLED_BY_WORKER` (a worker declining
    their own already-accepted job, handled entirely by
    `app/api/assignments.py`'s `cancel_assignment`) is a distinct,
    Assignment-level status; this endpoint only ever sets the
    ServiceRequest-level `CANCELLED_BY_USER`.
    """
    profile = _get_own_user_profile(db, account)
    service_request = _lock_own_request(db, profile, request_id)

    if service_request.status not in _USER_CANCELLABLE_STATUSES:
        raise conflict("Service request is not in a state that can be cancelled")

    service_request.status = ServiceRequestStatus.CANCELLED_BY_USER

    db.flush()
    db.refresh(service_request)

    return ServiceRequestPublic.model_validate(service_request)
