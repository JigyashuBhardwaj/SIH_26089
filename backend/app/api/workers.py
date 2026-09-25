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
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.errors import not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.assignment import Assignment
from app.models.enums import AccountRole
from app.models.service_request import ServiceRequest
from app.models.worker import Worker
from app.schemas.assignment import (
    AssignmentRequestSummary,
    WorkerAssignmentListResponse,
    WorkerAssignmentPublic,
)
from app.schemas.pagination import PaginationParams
from app.schemas.worker import WorkerPublic

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
