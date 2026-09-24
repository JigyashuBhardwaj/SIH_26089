"""
Phase 5E-D: ASSOCIATION_ADMIN read-only routes over their own association's
workers and service requests.

`GET /associations/me/workers`               — list workers belonging to the
                                                 authenticated admin's own association.
`GET /associations/me/requests`               — list ServiceRequests belonging to the
                                                 authenticated admin's own association.
`GET /associations/me/requests/{request_id}`  — retrieve a single one of those requests.

Phase 5E-E adds the one manual-assignment write operation:

`POST /associations/me/requests/{request_id}/assignments` — manually assign a
    Worker (from the same association) to a ServiceRequest, transitioning it
    PENDING/MATCHING -> ASSIGNED and appending a new Assignment row. This is
    the ONLY mutation on this router — no other lifecycle transition, no
    automatic worker selection/ranking, and Assignment history is
    append-only (a new row is always added, never overwritten).

Scope is always derived from the authenticated Account's own
`association_id` column — never from a client-supplied id.
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
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus, WorkerStatus
from app.models.service_request import ServiceRequest
from app.models.worker import Worker
from app.models.worker_skill import WorkerSkill
from app.schemas.assignment import AssignmentCreate, AssignmentPublic
from app.schemas.pagination import PaginationParams
from app.schemas.request import ServiceRequestListResponse, ServiceRequestPublic
from app.schemas.worker import WorkerListResponse, WorkerPublic

router = APIRouter(prefix="/associations", tags=["associations"])

# Assignment statuses that count as "currently active" for a ServiceRequest
# — i.e. still awaiting a worker's response or already accepted and being
# worked. DECLINED/CANCELLED_BY_WORKER/COMPLETED are terminal/historical
# and never block a new assignment on their own (the request's own status
# check below is what actually gates re-assignment in the normal case);
# this is a defense-in-depth check against a request that is still
# PENDING/MATCHING despite already having an unresolved assignment.
_ACTIVE_ASSIGNMENT_STATUSES = (AssignmentStatus.PENDING_RESPONSE, AssignmentStatus.ACCEPTED)


def _require_own_association_id(account: Account) -> UUID:
    """
    Resolve the authenticated ASSOCIATION_ADMIN's own association_id.
    404 if the account has no association linked (there is no legitimate
    ASSOCIATION_ADMIN account without one, but the column is nullable at
    the database level, so this is handled explicitly rather than assumed).
    """
    if account.association_id is None:
        raise not_found("No association is linked to this account")
    return account.association_id


@router.get("/me/workers", response_model=WorkerListResponse)
def list_own_association_workers(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.ASSOCIATION_ADMIN)),
) -> WorkerListResponse:
    """
    List workers belonging to the authenticated admin's own association,
    ordered by `full_name ASC` with `id ASC` as a stable tiebreaker.
    """
    association_id = _require_own_association_id(account)

    base_query = select(Worker).where(Worker.association_id == association_id)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    workers = (
        db.execute(
            base_query.order_by(Worker.full_name.asc(), Worker.id.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    return WorkerListResponse(
        items=[WorkerPublic.model_validate(worker) for worker in workers],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/me/requests", response_model=ServiceRequestListResponse)
def list_own_association_requests(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.ASSOCIATION_ADMIN)),
) -> ServiceRequestListResponse:
    """
    List ServiceRequests belonging to the authenticated admin's own
    association, newest first (`created_at DESC`, `id DESC` tiebreaker).
    """
    association_id = _require_own_association_id(account)

    base_query = select(ServiceRequest).where(
        ServiceRequest.association_id == association_id
    )

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

    return ServiceRequestListResponse(
        items=[
            ServiceRequestPublic.model_validate(service_request)
            for service_request in service_requests
        ],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/me/requests/{request_id}", response_model=ServiceRequestPublic)
def get_own_association_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.ASSOCIATION_ADMIN)),
) -> ServiceRequestPublic:
    """
    Return a single ServiceRequest, only if it belongs to the
    authenticated admin's own association. A nonexistent request and a
    request belonging to another association both return 404.
    """
    association_id = _require_own_association_id(account)

    service_request = db.execute(
        select(ServiceRequest).where(
            ServiceRequest.id == request_id,
            ServiceRequest.association_id == association_id,
        )
    ).scalar_one_or_none()

    if service_request is None:
        raise not_found("Service request not found")

    return ServiceRequestPublic.model_validate(service_request)


@router.post(
    "/me/requests/{request_id}/assignments",
    response_model=AssignmentPublic,
    status_code=201,
)
def create_assignment(
    request_id: UUID,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.ASSOCIATION_ADMIN)),
) -> AssignmentPublic:
    """
    Manually assign a Worker to a ServiceRequest belonging to the
    authenticated admin's own association.

    Both the ServiceRequest and the target Worker must belong to that
    same association — one from another association is indistinguishable
    from nonexistent (404). Only a request currently PENDING or MATCHING
    may be assigned; any other status, an already-active assignment on
    the request, an inactive worker, or a worker lacking the request's
    service (via WorkerSkill) all reject with 409. On success, a new
    Assignment row is appended (history is never overwritten) with
    status PENDING_RESPONSE, and the ServiceRequest transitions to
    ASSIGNED — both changes are flushed together in the same
    request-scoped session/transaction, so a rejected request never
    leaves a partial update: every validation above runs before either
    write is made.

    Concurrency: the ServiceRequest row is locked with `SELECT ... FOR
    UPDATE` (`with_for_update()`) as the very first step, before any of
    the state checks below run, and held for the rest of this
    transaction. Two concurrent assignment attempts against the same
    request can therefore never both observe it as PENDING/MATCHING with
    no active assignment — the second admin's request blocks until the
    first's transaction ends (flush/rollback), by which point the
    request's status/active-assignment state already reflects the
    first's outcome, so the second is correctly rejected with 409 rather
    than racing to create a second Assignment.
    """
    association_id = _require_own_association_id(account)

    # Step 1: lock the ServiceRequest row for the duration of this
    # transaction, before checking anything about it, so no other
    # transaction can concurrently read-then-write the same row in the
    # window between this check and the writes below.
    service_request = db.execute(
        select(ServiceRequest)
        .where(ServiceRequest.id == request_id)
        .with_for_update()
    ).scalar_one_or_none()

    # Step 2: verify it belongs to the authenticated admin's association.
    # A nonexistent request and one belonging to another association are
    # indistinguishable (both 404).
    if service_request is None or service_request.association_id != association_id:
        raise not_found("Service request not found")

    # Step 3: verify its status is PENDING or MATCHING.
    if service_request.status not in (
        ServiceRequestStatus.PENDING,
        ServiceRequestStatus.MATCHING,
    ):
        raise conflict("Service request is not in a state that can be assigned")

    # Step 4: check for an existing active Assignment (defense-in-depth
    # against a request that is still PENDING/MATCHING despite already
    # having an unresolved assignment).
    existing_active_assignment = db.execute(
        select(Assignment).where(
            Assignment.request_id == service_request.id,
            Assignment.status.in_(_ACTIVE_ASSIGNMENT_STATUSES),
        )
    ).scalar_one_or_none()
    if existing_active_assignment is not None:
        raise conflict("This service request already has an active assignment")

    # Step 5: validate the selected Worker and WorkerSkill.
    worker = db.execute(
        select(Worker).where(
            Worker.id == payload.worker_id,
            Worker.association_id == association_id,
        )
    ).scalar_one_or_none()
    if worker is None:
        raise not_found("Worker not found")

    if worker.status != WorkerStatus.ACTIVE:
        raise conflict("Worker is not active")

    has_required_skill = db.execute(
        select(WorkerSkill).where(
            WorkerSkill.worker_id == worker.id,
            WorkerSkill.service_id == service_request.service_id,
        )
    ).scalar_one_or_none()
    if has_required_skill is None:
        raise conflict("Worker does not have the service required by this request")

    # Step 6: create the Assignment with PENDING_RESPONSE.
    assignment = Assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=account.id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )
    db.add(assignment)

    # Step 7: transition the ServiceRequest to ASSIGNED.
    service_request.status = ServiceRequestStatus.ASSIGNED

    # Step 8: flush both changes atomically, in the same transaction that
    # is still holding the row lock acquired in step 1.
    db.flush()
    db.refresh(assignment)

    return AssignmentPublic.model_validate(assignment)
