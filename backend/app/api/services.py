"""
Phase 5E-B: read-only service catalogue routes.

`GET /services` — the active service catalogue, paginated.
`GET /services/{service_id}` — a single active service.

Both are authenticated (any authenticated role may browse the
catalogue); neither exposes the SQLAlchemy `Service` model directly.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth.dependencies import get_current_account
from app.database import get_db
from app.models.account import Account
from app.models.service import Service
from app.schemas.pagination import PaginationParams
from app.schemas.service import ServiceListResponse, ServicePublic

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=ServiceListResponse)
def list_services(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _account: Account = Depends(get_current_account),
) -> ServiceListResponse:
    """
    Return the active service catalogue (`is_active = True` only),
    ordered by name ascending for a deterministic, stable page order.
    """
    base_query = select(Service).where(Service.is_active.is_(True))

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    services = (
        db.execute(
            base_query.order_by(Service.name.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    return ServiceListResponse(
        items=[ServicePublic.model_validate(service) for service in services],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get("/{service_id}", response_model=ServicePublic)
def get_service(
    service_id: UUID,
    db: Session = Depends(get_db),
    _account: Account = Depends(get_current_account),
) -> ServicePublic:
    """
    Return a single active service by id. An inactive or nonexistent
    service both behave as 404 — a client cannot distinguish "doesn't
    exist" from "exists but inactive" through this endpoint.
    """
    service = db.execute(
        select(Service).where(Service.id == service_id, Service.is_active.is_(True))
    ).scalar_one_or_none()

    if service is None:
        raise not_found("Service not found")

    return ServicePublic.model_validate(service)
