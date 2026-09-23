"""
Reusable organization-scope foundations for future protected routes.

Phase 5D defines no business/domain API routes, so nothing here is wired
into an endpoint yet — these are the building blocks a later phase's
routes will call. The rule they all share: organization scope is always
re-derived from the authenticated `Account`'s own database relationships,
never taken from a client-supplied ID (a request body/query/path
`association_id`, `federation_id`, or `worker_id`). Changing such an ID in
a request must never grant access to another organization's data.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.association import Association
from app.models.worker import Worker


def _forbidden(detail: str = "You do not have access to this resource") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_worker_association_id(db: Session, account: Account) -> UUID:
    """
    Derive a WORKER account's own association_id from its Worker row —
    i.e. Account -> Worker -> Association, per the locked worker scope
    design. Never accepts a worker/association id as a parameter: the
    only input is the authenticated Account itself.
    """
    worker = db.execute(
        select(Worker).where(Worker.account_id == account.id)
    ).scalar_one_or_none()
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No worker profile is linked to this account",
        )
    return worker.association_id


def ensure_association_admin_scope(account: Account, target_association_id: UUID) -> None:
    """
    Enforce that an ASSOCIATION_ADMIN account may only act on its own
    Association. `account.association_id` comes from the database-loaded
    Account row (set at login time, never from client input); raises 403
    if it doesn't match `target_association_id`, whatever the caller
    intended to access.
    """
    if account.association_id is None or account.association_id != target_association_id:
        raise _forbidden("You do not have access to this association")


def get_federation_association_ids(db: Session, account: Account) -> list[UUID]:
    """
    All Association ids belonging to a FEDERATION_ADMIN account's own
    federation (Federation -> Associations), derived from
    `account.federation_id` — never from a client-supplied federation id.
    """
    rows = db.execute(
        select(Association.id).where(Association.federation_id == account.federation_id)
    ).scalars()
    return list(rows)


def ensure_federation_admin_scope(
    db: Session, account: Account, target_association_id: UUID
) -> None:
    """
    Enforce that a FEDERATION_ADMIN account may only act on an
    Association that belongs to its own Federation. Note this grants
    visibility/read-style scope only — per the locked Phase 5D design, a
    FEDERATION_ADMIN does NOT automatically receive ASSOCIATION_ADMIN's
    operational permissions (e.g. worker-allocation authority), so a
    future route must not treat passing this check as equivalent to
    passing `ensure_association_admin_scope`.
    """
    if target_association_id not in get_federation_association_ids(db, account):
        raise _forbidden("You do not have access to this association")
