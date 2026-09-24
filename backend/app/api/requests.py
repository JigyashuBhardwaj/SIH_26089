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
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
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
