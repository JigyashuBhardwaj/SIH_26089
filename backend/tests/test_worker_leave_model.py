"""
Phase 7C-B: minimal structural/model tests for the new `WorkerLeave`
table and `LeaveStatus` enum.

This phase introduces ONLY the database foundation -- no API, no
business-rule validation (no minimum duration, no notice period, no
annual quota, no overlap check). Accordingly these tests cover ONLY what
7C-B actually built: that a `WorkerLeave` row can be constructed with
valid fields, that its default status is PENDING, and that the one
structural CHECK constraint (`end_at >= start_at`) is enforced by the
database. Full business-rule test coverage belongs to the later 7C
sub-phase that actually implements those rules.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.enums import AccountRole
from app.models.worker_leave import LeaveStatus, WorkerLeave


def _federation_association_worker(
    make_federation, make_association, make_account, make_worker
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=association.id)
    return federation, association, worker


# ===================================================== MODEL / DATABASE ===


def test_worker_leave_can_be_constructed_with_valid_fields(
    make_federation, make_association, make_account, make_worker, db_session
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=2)

    leave = WorkerLeave(worker_id=worker.id, start_at=start_at, end_at=end_at)
    db_session.add(leave)
    db_session.flush()
    db_session.refresh(leave)

    assert leave.id is not None
    assert leave.worker_id == worker.id
    assert leave.start_at == start_at
    assert leave.end_at == end_at
    assert leave.reviewed_by is None
    assert leave.reviewed_at is None
    assert leave.created_at is not None
    assert leave.updated_at is not None


def test_worker_leave_default_status_is_pending(
    make_federation, make_association, make_account, make_worker, db_session
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=1)

    leave = WorkerLeave(worker_id=worker.id, start_at=start_at, end_at=end_at)
    db_session.add(leave)
    db_session.flush()
    db_session.refresh(leave)

    assert leave.status == LeaveStatus.PENDING


def test_worker_leave_can_be_constructed_with_each_status(
    make_federation, make_association, make_account, make_worker, db_session
):
    """
    Structural-only: confirms the VARCHAR+CHECK column accepts all three
    locked status values (and only these three -- CANCELLED is
    deliberately not a member of `LeaveStatus` at all, so there is no
    rejection case to test for it here; Python's own enum would reject an
    unknown member before a row is ever built).
    """
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=1)

    for status in (LeaveStatus.PENDING, LeaveStatus.APPROVED, LeaveStatus.REJECTED):
        leave = WorkerLeave(worker_id=worker.id, start_at=start_at, end_at=end_at, status=status)
        db_session.add(leave)
        db_session.flush()
        db_session.refresh(leave)
        assert leave.status == status


def test_worker_leave_end_at_before_start_at_is_rejected(
    make_federation, make_association, make_account, make_worker, db_session
):
    """
    The one structural constraint this phase adds:
    `ck_worker_leaves_end_at_after_start_at`. This is NOT the later
    minimum-1-day-duration business rule -- a same-instant `start_at ==
    end_at` is structurally valid (`>=`, not `>`) and deliberately not
    rejected here.
    """
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at - timedelta(hours=1)

    with pytest.raises(IntegrityError):
        leave = WorkerLeave(worker_id=worker.id, start_at=start_at, end_at=end_at)
        db_session.add(leave)
        db_session.flush()
    db_session.rollback()


def test_worker_leave_end_at_equal_to_start_at_is_accepted(
    make_federation, make_association, make_account, make_worker, db_session
):
    """The structural constraint is inclusive (`>=`), not exclusive."""
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    same_instant = datetime.now(timezone.utc) + timedelta(days=3)

    leave = WorkerLeave(worker_id=worker.id, start_at=same_instant, end_at=same_instant)
    db_session.add(leave)
    db_session.flush()
    db_session.refresh(leave)

    assert leave.end_at == leave.start_at


def test_worker_leave_reviewed_fields_can_be_set(
    make_federation, make_association, make_account, make_worker, db_session
):
    """
    `reviewed_by`/`reviewed_at` are nullable (a PENDING leave has not
    been reviewed yet) but must accept a value once set -- this phase
    does not implement the approval endpoint itself, only the columns it
    will eventually write to.
    """
    _, association, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    admin_account = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=1)
    reviewed_at = datetime.now(timezone.utc)

    leave = WorkerLeave(
        worker_id=worker.id,
        start_at=start_at,
        end_at=end_at,
        status=LeaveStatus.APPROVED,
        reviewed_by=admin_account.id,
        reviewed_at=reviewed_at,
    )
    db_session.add(leave)
    db_session.flush()
    db_session.refresh(leave)

    assert leave.reviewed_by == admin_account.id
    assert leave.reviewed_at == reviewed_at


def test_worker_leave_worker_id_must_reference_existing_worker(
    make_federation, make_association, make_account, make_worker, db_session
):
    """FK constraint: a nonexistent worker_id must be rejected, not silently accepted."""
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=1)

    with pytest.raises(IntegrityError):
        leave = WorkerLeave(worker_id=uuid.uuid4(), start_at=start_at, end_at=end_at)
        db_session.add(leave)
        db_session.flush()
    db_session.rollback()


def test_worker_leaves_relationship_is_navigable_from_worker(
    make_federation, make_association, make_account, make_worker, db_session
):
    """`Worker.leaves` (the one relationship this phase adds to Worker) returns this row."""
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=1)

    leave = WorkerLeave(worker_id=worker.id, start_at=start_at, end_at=end_at)
    db_session.add(leave)
    db_session.flush()
    db_session.refresh(worker)

    assert leave in worker.leaves
