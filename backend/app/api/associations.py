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

Phase 5E-H adds one more READ-ONLY operation:

`GET /associations/me/requests/{request_id}/candidates` — list eligible
    Workers for a ServiceRequest in a deterministic ranking order, so the
    admin can decide who to manually assign via the endpoint above. This
    endpoint never creates, modifies, or selects an Assignment, and never
    mutates the ServiceRequest — it only reads and ranks.

Scope for all `/associations/me/*` routes above is always derived from the
authenticated Account's own `association_id` column — never from a
client-supplied id.

Phase 6B-pre adds one more, unrelated, top-level route:

`GET /associations` — a plain, public-style directory listing of every
    Association row (id, federationId, name only — no worker/request data),
    open to ANY authenticated role. This exists so a USER-role client (the
    mobile booking flow) can resolve real backend Association UUIDs instead
    of relying on a hardcoded/local id list, mirroring the existing
    `GET /services` catalogue route's posture exactly. It is intentionally
    separate from the `/me/*` sub-resource above: it grants no access to any
    association's private operational data, and does not touch any existing
    route, scope helper, or role guard.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.errors import conflict, not_found
from app.auth.dependencies import get_current_account, require_role
from app.database import get_db
from app.models.account import Account
from app.models.assignment import Assignment
from app.models.association import Association
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus, WorkerStatus
from app.models.service_request import ServiceRequest
from app.models.worker import Worker
from app.models.worker_skill import WorkerSkill
from app.schemas.assignment import AssignmentCreate, AssignmentPublic
from app.schemas.association import AssociationListResponse, AssociationPublic
from app.schemas.candidate import CandidateListResponse, CandidatePublic
from app.schemas.pagination import PaginationParams
from app.schemas.request import ServiceRequestListResponse, ServiceRequestPublic
from app.schemas.worker import WorkerListResponse, WorkerPublic

router = APIRouter(prefix="/associations", tags=["associations"])


@router.get("", response_model=AssociationListResponse)
def list_associations(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _account: Account = Depends(get_current_account),
) -> AssociationListResponse:
    """
    Return every Association row, paginated, ordered by `name ASC` with
    `id ASC` as a stable tiebreaker. Any authenticated role may call this —
    it is a public directory listing (id/federationId/name only), not a
    view into any association's private workers or requests, so it does
    not need `require_role`/association-scope enforcement the way
    `/associations/me/*` does.
    """
    base_query = select(Association)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    associations = (
        db.execute(
            base_query.order_by(Association.name.asc(), Association.id.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    return AssociationListResponse(
        items=[AssociationPublic.model_validate(association) for association in associations],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


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


@router.get(
    "/me/requests/{request_id}/candidates",
    response_model=CandidateListResponse,
)
def list_candidates_for_request(
    request_id: UUID,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.ASSOCIATION_ADMIN)),
) -> CandidateListResponse:
    """
    Phase 5E-H: read-only candidate discovery for a ServiceRequest
    belonging to the authenticated admin's own association. Returns
    eligible Workers in a deterministic ranking order so the admin can
    decide who to assign — it never creates, modifies, or auto-selects an
    Assignment, and never mutates the ServiceRequest. The admin still
    calls the existing `POST .../assignments` endpoint above to actually
    assign a chosen worker.

    Eligibility — a Worker qualifies only if ALL of:
      1. Worker.association_id == the request's association_id (workers
         from another association never appear).
      2. Worker.status == ACTIVE (inactive workers are excluded).
      3. The Worker has a WorkerSkill for the request's service_id.
      4. No availability conflict: the Worker has no OTHER Assignment
         (i.e. not one on this same request) with status PENDING_RESPONSE
         or ACCEPTED whose own ServiceRequest shares this request's exact
         `requested_date_time`. DECLINED/CANCELLED_BY_WORKER/COMPLETED
         assignments never conflict. There is deliberately no leave or
         service-duration model yet, so this same-datetime check is the
         full extent of availability logic in this phase.
      5. Worker.pincode is NEVER an eligibility filter — a different
         pincode only affects ranking (below), never exclusion. Pincodes
         are compared for exact equality only; this is not a distance or
         geocoding calculation.

    Ranking — deterministic lexicographic ordering, no weighted score:
      1. same pincode as the request first
      2. fewer active (PENDING_RESPONSE/ACCEPTED) assignments first
      3. higher rating first
      4. Worker.id ascending, as the final deterministic tiebreaker
    `total_jobs_completed` and `worker_code` are never ranking factors.

    Only a request currently PENDING or MATCHING can be searched for
    candidates; any other status (it already has an active assignment, or
    has moved past matching entirely) returns 409.
    """
    association_id = _require_own_association_id(account)

    service_request = db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id)
    ).scalar_one_or_none()

    # A nonexistent request and one belonging to another association are
    # indistinguishable (both 404) — never leak cross-association info.
    if service_request is None or service_request.association_id != association_id:
        raise not_found("Service request not found")

    if service_request.status not in (
        ServiceRequestStatus.PENDING,
        ServiceRequestStatus.MATCHING,
    ):
        raise conflict("Service request is not in a state that can be matched")

    # Availability conflict: an active Assignment (on some OTHER request)
    # belonging to this worker, whose own ServiceRequest shares this
    # request's exact requested_date_time. Correlated to the outer
    # `Worker` row and evaluated by the database itself as part of the
    # single query below — never a per-worker Python-side round trip.
    conflicting_assignment_exists = (
        select(Assignment.id)
        .join(ServiceRequest, Assignment.request_id == ServiceRequest.id)
        .where(
            Assignment.worker_id == Worker.id,
            Assignment.status.in_(_ACTIVE_ASSIGNMENT_STATUSES),
            Assignment.request_id != service_request.id,
            ServiceRequest.requested_date_time == service_request.requested_date_time,
        )
        .correlate(Worker)
        .exists()
    )

    has_required_skill = (
        select(WorkerSkill.worker_id)
        .where(
            WorkerSkill.worker_id == Worker.id,
            WorkerSkill.service_id == service_request.service_id,
        )
        .correlate(Worker)
        .exists()
    )

    # Total count of ALL of this worker's currently active assignments
    # (not limited to the same datetime) — this is the "workload" ranking
    # factor, distinct from the availability conflict check above.
    active_assignment_count = (
        select(func.count(Assignment.id))
        .where(
            Assignment.worker_id == Worker.id,
            Assignment.status.in_(_ACTIVE_ASSIGNMENT_STATUSES),
        )
        .correlate(Worker)
        .scalar_subquery()
    )

    is_same_pincode = Worker.pincode == service_request.pincode

    eligibility_filters = (
        Worker.association_id == association_id,
        Worker.status == WorkerStatus.ACTIVE,
        has_required_skill,
        ~conflicting_assignment_exists,
    )

    total = db.execute(
        select(func.count()).select_from(
            select(Worker.id).where(*eligibility_filters).subquery()
        )
    ).scalar_one()

    rows = db.execute(
        select(Worker, active_assignment_count.label("active_assignment_count"))
        .where(*eligibility_filters)
        .order_by(
            case((is_same_pincode, 0), else_=1).asc(),
            active_assignment_count.asc(),
            Worker.rating.desc(),
            Worker.id.asc(),
        )
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()

    items = [
        CandidatePublic(
            worker_id=worker.id,
            worker_code=worker.worker_code,
            full_name=worker.full_name,
            phone=worker.phone,
            address=worker.address,
            pincode=worker.pincode,
            rating=worker.rating,
            total_jobs_completed=worker.total_jobs_completed,
            active_assignment_count=active_count,
            same_pincode=(worker.pincode == service_request.pincode),
        )
        for worker, active_count in rows
    ]

    return CandidateListResponse(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )
