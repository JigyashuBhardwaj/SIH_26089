"""
Phase 5E-D: WORKER read-only routes over their own profile and assignment
history.

`GET /workers/me`              — the authenticated worker's own Worker profile.
`GET /workers/me/assignments`  — the authenticated worker's own Assignment history.

Identity is always derived from the authenticated Account -> its own
`Worker` row, never from a client-supplied id. READ-ONLY: no assignment
creation, response (accept/decline), or status mutation happens here.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.assignment import Assignment
from app.models.enums import AccountRole
from app.models.worker import Worker
from app.schemas.assignment import AssignmentListResponse, AssignmentPublic
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


@router.get("/me/assignments", response_model=AssignmentListResponse)
def list_own_assignments(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.WORKER)),
) -> AssignmentListResponse:
    """
    List only the authenticated worker's own Assignment history (no
    "active only" filter), ordered by `assigned_at DESC` with `id DESC`
    as a stable tiebreaker.
    """
    worker = _get_own_worker(db, account)

    base_query = select(Assignment).where(Assignment.worker_id == worker.id)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    assignments = (
        db.execute(
            base_query.order_by(Assignment.assigned_at.desc(), Assignment.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    return AssignmentListResponse(
        items=[AssignmentPublic.model_validate(assignment) for assignment in assignments],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )
