"""
Phase 7C-C: tests for the pure/reusable business-rule primitives in
`app.domain.leave_rules`.

These test the PRIMITIVES ONLY -- `leave_day_count`, `split_leave_days_by_year`,
`approved_leave_days_in_year`, `leave_overlaps_existing`, and
`leave_conflicts_accepted_assignment`. There is no leave submission or
approval API endpoint yet (explicitly out of scope for this phase), so
every test here calls the domain functions directly against `db_session`
and factory-created rows, the same way `test_worker_leave_model.py` tests
the `WorkerLeave` model directly rather than through an HTTP route.

All calendar-day assertions use the locked Asia/Kolkata reference
timezone. No `datetime.now()`/local-timezone call is used anywhere in
this file for calendar-day math -- only `datetime.now(timezone.utc)` for
picking realistic "future" timestamps, and `ZoneInfo("Asia/Kolkata")` for
constructing specific IST wall-clock times where the exact calendar date
matters.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.leave_rules import (
    MAX_ANNUAL_LEAVE_DAYS,
    approved_leave_days_in_year,
    leave_conflicts_accepted_assignment,
    leave_day_count,
    leave_overlaps_existing,
    split_leave_days_by_year,
    to_kolkata_date,
)
from app.models.enums import AccountRole, AssignmentStatus
from app.models.worker_leave import LeaveStatus

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def _ist(year, month, day, hour=12, minute=0) -> datetime:
    """Build a timezone-aware UTC datetime from an explicit IST wall-clock date/time."""
    return datetime(year, month, day, hour, minute, tzinfo=KOLKATA_TZ).astimezone(timezone.utc)


def _federation_association_worker(
    make_federation, make_association, make_account, make_worker
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=association.id)
    return federation, association, worker


# ===================================================== to_kolkata_date ===


def test_to_kolkata_date_converts_utc_evening_to_next_ist_day():
    """
    21:00 UTC is 02:30 IST the *next* calendar day (IST = UTC+5:30) --
    this is the exact kind of UTC/IST calendar-date mismatch every other
    test in this file relies on `to_kolkata_date` to get right.
    """
    utc_value = datetime(2026, 10, 5, 21, 0, tzinfo=timezone.utc)
    assert to_kolkata_date(utc_value) == datetime(2026, 10, 6).date()


def test_to_kolkata_date_rejects_naive_datetime():
    with pytest.raises(ValueError):
        to_kolkata_date(datetime(2026, 10, 5, 12, 0))


# ===================================================== leave_day_count ===


def test_leave_day_count_same_day_is_one():
    start = _ist(2026, 10, 10, hour=9)
    end = _ist(2026, 10, 10, hour=18)
    assert leave_day_count(start, end) == 1


def test_leave_day_count_multi_day():
    start = _ist(2026, 10, 10)
    end = _ist(2026, 10, 12)
    assert leave_day_count(start, end) == 3


# ============================================ split_leave_days_by_year ===


def test_split_leave_days_by_year_within_single_year():
    start = _ist(2026, 10, 10)
    end = _ist(2026, 10, 12)
    assert split_leave_days_by_year(start, end) == {2026: 3}


def test_split_leave_days_by_year_crosses_year_boundary():
    """30 Dec -> 2 Jan: 2 days in the old year, 2 days in the new year."""
    start = _ist(2026, 12, 30)
    end = _ist(2027, 1, 2)
    assert split_leave_days_by_year(start, end) == {2026: 2, 2027: 2}


# ====================================== approved_leave_days_in_year ===


def test_approved_leave_days_in_year_only_counts_approved(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 2, 1),
        end_at=_ist(2026, 2, 5),
        status=LeaveStatus.APPROVED,
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 3, 1),
        end_at=_ist(2026, 3, 5),
        status=LeaveStatus.PENDING,
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 4, 1),
        end_at=_ist(2026, 4, 5),
        status=LeaveStatus.REJECTED,
    )

    total = approved_leave_days_in_year(db_session, worker.id, 2026)

    # Only the 5-day APPROVED leave (1-5 Feb inclusive) counts -- the
    # PENDING and REJECTED rows must be entirely excluded.
    assert total == 5


def test_approved_leave_days_in_year_splits_across_years(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 12, 30),
        end_at=_ist(2027, 1, 2),
        status=LeaveStatus.APPROVED,
    )

    assert approved_leave_days_in_year(db_session, worker.id, 2026) == 2
    assert approved_leave_days_in_year(db_session, worker.id, 2027) == 2


def test_approved_quota_59_plus_1_day_leave_equals_60_within_cap(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    """
    A worker already at 59 approved days this year, with a candidate
    1-day leave, totals exactly 60 -- at, not over, `MAX_ANNUAL_LEAVE_DAYS`.
    This module computes totals only (no accept/reject decision exists
    yet -- that belongs to the future approval endpoint), so this test
    demonstrates the arithmetic that endpoint will rely on.
    """
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    # 59 approved days: 1 Jan through 28 Feb 2026 inclusive (31 + 28 = 59).
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 2, 28),
        status=LeaveStatus.APPROVED,
    )
    existing_total = approved_leave_days_in_year(db_session, worker.id, 2026)
    assert existing_total == 59

    candidate_days = leave_day_count(_ist(2026, 3, 1), _ist(2026, 3, 1))
    assert existing_total + candidate_days == MAX_ANNUAL_LEAVE_DAYS


def test_approved_quota_60_plus_1_day_leave_exceeds_cap(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    """A worker already at exactly 60 approved days: one more day would exceed the cap."""
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    # 60 approved days: 1 Jan through 1 Mar 2026 inclusive (31 + 28 + 1 = 60).
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 3, 1),
        status=LeaveStatus.APPROVED,
    )
    existing_total = approved_leave_days_in_year(db_session, worker.id, 2026)
    assert existing_total == MAX_ANNUAL_LEAVE_DAYS

    candidate_days = leave_day_count(_ist(2026, 3, 2), _ist(2026, 3, 2))
    assert existing_total + candidate_days > MAX_ANNUAL_LEAVE_DAYS


def test_approved_leave_days_in_year_exclude_leave_id(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    """`exclude_leave_id` omits one specific row -- for a future approval
    endpoint recomputing "the total without the row I'm about to approve"."""
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 5, 1),
        end_at=_ist(2026, 5, 10),
        status=LeaveStatus.APPROVED,
    )

    assert approved_leave_days_in_year(db_session, worker.id, 2026) == 10
    assert (
        approved_leave_days_in_year(
            db_session, worker.id, 2026, exclude_leave_id=leave.id
        )
        == 0
    )


# ============================================== leave_overlaps_existing ===


def test_pending_leave_blocks_overlap(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.PENDING,
    )

    assert leave_overlaps_existing(
        db_session, worker.id, _ist(2026, 10, 11), _ist(2026, 10, 13)
    )


def test_approved_leave_blocks_overlap(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.APPROVED,
    )

    assert leave_overlaps_existing(
        db_session, worker.id, _ist(2026, 10, 11), _ist(2026, 10, 13)
    )


def test_rejected_leave_does_not_block_overlap(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.REJECTED,
    )

    assert not leave_overlaps_existing(
        db_session, worker.id, _ist(2026, 10, 11), _ist(2026, 10, 13)
    )


def test_overlap_is_inclusive_at_touching_endpoint(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    """
    Locked product decision: 10-12 Oct and 12-14 Oct DO overlap (they
    share 12 Oct) -- inclusive boundary semantics, not a half-open
    interval.
    """
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.APPROVED,
    )

    assert leave_overlaps_existing(
        db_session, worker.id, _ist(2026, 10, 12), _ist(2026, 10, 14)
    )


def test_non_overlapping_ranges_do_not_overlap(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.APPROVED,
    )

    assert not leave_overlaps_existing(
        db_session, worker.id, _ist(2026, 10, 13), _ist(2026, 10, 15)
    )


def test_different_worker_does_not_conflict(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    federation, association, worker_one = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    worker_two_account = make_account(role=AccountRole.WORKER)
    worker_two = make_worker(account_id=worker_two_account.id, association_id=association.id)

    make_worker_leave(
        worker_id=worker_one.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.APPROVED,
    )

    assert not leave_overlaps_existing(
        db_session, worker_two.id, _ist(2026, 10, 10), _ist(2026, 10, 12)
    )


def test_overlap_excludes_the_given_leave_id(
    make_federation, make_association, make_account, make_worker,
    make_worker_leave, db_session,
):
    """
    `exclude_leave_id` lets a future approval endpoint re-check a leave
    against every OTHER leave without it conflicting with itself.
    """
    _, _, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 10),
        end_at=_ist(2026, 10, 12),
        status=LeaveStatus.PENDING,
    )

    assert leave_overlaps_existing(
        db_session, worker.id, _ist(2026, 10, 10), _ist(2026, 10, 12)
    )
    assert not leave_overlaps_existing(
        db_session,
        worker.id,
        _ist(2026, 10, 10),
        _ist(2026, 10, 12),
        exclude_leave_id=leave.id,
    )


# ===================================== leave_conflicts_accepted_assignment ===


def test_accepted_assignment_conflicts_with_leave(
    make_federation, make_association, make_account, make_worker,
    make_service, make_worker_skill, make_user_profile, make_service_request,
    make_assignment, db_session,
):
    federation, association, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)
    user_account = make_account(role=AccountRole.USER)
    user_profile = make_user_profile(account_id=user_account.id)
    admin_account = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    service_request = make_service_request(
        user_id=user_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=_ist(2026, 10, 11, hour=14),
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin_account.id,
        status=AssignmentStatus.ACCEPTED,
    )

    assert leave_conflicts_accepted_assignment(
        db_session, worker.id, _ist(2026, 10, 10), _ist(2026, 10, 12)
    )


def test_non_accepted_assignment_does_not_conflict(
    make_federation, make_association, make_account, make_worker,
    make_service, make_worker_skill, make_user_profile, make_service_request,
    make_assignment, db_session,
):
    federation, association, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)
    user_account = make_account(role=AccountRole.USER)
    user_profile = make_user_profile(account_id=user_account.id)
    admin_account = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    service_request = make_service_request(
        user_id=user_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=_ist(2026, 10, 11, hour=14),
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin_account.id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )

    assert not leave_conflicts_accepted_assignment(
        db_session, worker.id, _ist(2026, 10, 10), _ist(2026, 10, 12)
    )


def test_accepted_assignment_outside_leave_range_does_not_conflict(
    make_federation, make_association, make_account, make_worker,
    make_service, make_worker_skill, make_user_profile, make_service_request,
    make_assignment, db_session,
):
    federation, association, worker = _federation_association_worker(
        make_federation, make_association, make_account, make_worker
    )
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)
    user_account = make_account(role=AccountRole.USER)
    user_profile = make_user_profile(account_id=user_account.id)
    admin_account = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    service_request = make_service_request(
        user_id=user_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=_ist(2026, 10, 20, hour=14),
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin_account.id,
        status=AssignmentStatus.ACCEPTED,
    )

    assert not leave_conflicts_accepted_assignment(
        db_session, worker.id, _ist(2026, 10, 10), _ist(2026, 10, 12)
    )
