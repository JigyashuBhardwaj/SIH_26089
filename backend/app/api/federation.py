"""
Phase 5E-D: FEDERATION_ADMIN read-only routes over associations and
workers under their own federation.

`GET /federation/me/associations`  — associations belonging to the authenticated
                                      admin's own federation.
`GET /federation/me/workers`       — workers belonging to any association under the
                                      authenticated admin's own federation.

Scope is always derived from the authenticated Account's own
`federation_id` column (and, for workers, the existing
`get_federation_association_ids` scope helper) — never from a
client-supplied id. READ-ONLY: a federation admin may view but never
modify or allocate workers, per the locked spec.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth.dependencies import require_role
from app.auth.scope import get_federation_association_ids
from app.database import get_db
from app.models.account import Account
from app.models.association import Association
from app.models.enums import AccountRole
from app.models.worker import Worker
from app.schemas.association import AssociationListResponse, AssociationPublic
from app.schemas.pagination import PaginationParams
from app.schemas.worker import WorkerListResponse, WorkerPublic

router = APIRouter(prefix="/federation", tags=["federation"])


def _require_own_federation_id(account: Account):
    """
    Resolve the authenticated FEDERATION_ADMIN's own federation_id. 404 if
    the account has no federation linked (the column is nullable at the
    database level, so this is handled explicitly rather than assumed).
    """
    if account.federation_id is None:
        raise not_found("No federation is linked to this account")
    return account.federation_id


@router.get("/me/associations", response_model=AssociationListResponse)
def list_own_federation_associations(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.FEDERATION_ADMIN)),
) -> AssociationListResponse:
    """
    List associations belonging to the authenticated admin's own
    federation, ordered by `name ASC` with `id ASC` as a stable tiebreaker.
    """
    federation_id = _require_own_federation_id(account)

    base_query = select(Association).where(Association.federation_id == federation_id)

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


@router.get("/me/workers", response_model=WorkerListResponse)
def list_own_federation_workers(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.FEDERATION_ADMIN)),
) -> WorkerListResponse:
    """
    List workers belonging to any association under the authenticated
    admin's own federation, ordered by `full_name ASC` with `id ASC` as a
    stable tiebreaker.
    """
    # Also validates the account has a federation linked (404 otherwise),
    # consistent with the associations endpoint above.
    _require_own_federation_id(account)
    association_ids = get_federation_association_ids(db, account)

    base_query = select(Worker).where(Worker.association_id.in_(association_ids))

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
