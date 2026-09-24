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
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import conflict, not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.association import Association
from app.models.enums import AccountRole, ServiceRequestStatus
from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.user_profile import UserProfile
from app.schemas.pagination import PaginationParams
from app.schemas.request import (
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestPublic,
)

router = APIRouter(prefix="/requests", tags=["requests"])


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

    return ServiceRequestListResponse(
        items=[
            ServiceRequestPublic.model_validate(service_request)
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

    return ServiceRequestPublic.model_validate(service_request)


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
