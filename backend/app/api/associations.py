"""
Phase 5E-D: ASSOCIATION_ADMIN read-only routes over their own association's
workers and service requests.

`GET /associations/me/workers`               — list workers belonging to the
                                                 authenticated admin's own association.
`GET /associations/me/requests`               — list ServiceRequests belonging to the
                                                 authenticated admin's own association.
`GET /associations/me/requests/{request_id}`  — retrieve a single one of those requests.

Scope is always derived from the authenticated Account's own
`association_id` column — never from a client-supplied id. This router is
READ-ONLY: no worker allocation, request mutation, assignment creation, or
matching happens here.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.enums import AccountRole
from app.models.service_request import ServiceRequest
from app.models.worker import Worker
from app.schemas.pagination import PaginationParams
from app.schemas.request import ServiceRequestListResponse, ServiceRequestPublic
from app.schemas.worker import WorkerListResponse, WorkerPublic

router = APIRouter(prefix="/associations", tags=["associations"])


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
