"""
Tests for the Phase 7C-E ASSOCIATION_ADMIN leave-decision routes:
`POST /associations/me/leaves/{leave_id}/approve`,
`POST /associations/me/leaves/{leave_id}/reject`.

Mirrors `tests/test_associations.py`'s structural conventions (local
helpers, explicit cross-association/role checks). This file tests the
HTTP-level routes only -- the pure business-rule primitives they call
(`leave_overlaps_existing`, `leave_conflicts_accepted_assignment`,
`approved_leave_days_in_year`, `split_leave_days_by_year`) are already
tested directly in `tests/test_worker_leave_rules.py` and are not
re-tested here; the worker-submission route is tested in
`tests/test_worker_leaves_api.py` and is unaffected by this phase.
"""

import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.domain.leave_rules import approved_leave_days_in_year
from app.models.enums import AccountRole, AssignmentStatus
from app.models.worker_leave import LeaveStatus

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def _at_ist_days_ahead(days_ahead: int, hour: int = 12) -> datetime:
    """Same helper as `tests/test_worker_leaves_api.py` -- a UTC datetime
    whose Asia/Kolkata calendar date is `days_ahead` IST days from today."""
    today_ist = datetime.now(KOLKATA_TZ).date()
    target_date = today_ist + timedelta(days=days_ahead)
    target_ist = datetime.combine(target_date, time(hour=hour), tzinfo=KOLKATA_TZ)
    return target_ist.astimezone(timezone.utc)


def _ist(year, month, day, hour=12) -> datetime:
    """Build a timezone-aware UTC datetime from an explicit IST wall-clock date."""
    return datetime(year, month, day, hour, 0, tzinfo=KOLKATA_TZ).astimezone(timezone.utc)


def _make_federation_and_association(make_federation, make_association):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    return federation, association


def _make_worker_account(make_account, make_worker, *, association_id, full_name="Test Worker"):
    account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=account.id, association_id=association_id, full_name=full_name)
    return account, worker


def _approve_url(leave_id) -> str:
    return f"/associations/me/leaves/{leave_id}/approve"


def _reject_url(leave_id) -> str:
    return f"/associations/me/leaves/{leave_id}/reject"


# ======================================================== Authorization ===


def test_admin_can_approve_own_association_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 200
    assert response.json()["status"] == LeaveStatus.APPROVED.value


def test_admin_can_reject_own_association_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    response = client.post(_reject_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 200
    assert response.json()["status"] == LeaveStatus.REJECTED.value


def test_admin_cannot_approve_another_associations_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association_a = _make_federation_and_association(make_federation, make_association)
    association_b = make_association(federation_id=federation.id)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association_a.id)
    other_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association_b.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(other_admin))

    assert response.status_code == 404


def test_admin_cannot_reject_another_associations_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association_a = _make_federation_and_association(make_federation, make_association)
    association_b = make_association(federation_id=federation.id)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association_a.id)
    other_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association_b.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    response = client.post(_reject_url(leave.id), headers=auth_header(other_admin))

    assert response.status_code == 404


def test_user_role_forbidden_on_both_routes(
    client, make_account, make_worker, make_user_profile, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    assert client.post(_approve_url(leave.id), headers=auth_header(user_account)).status_code == 403
    assert client.post(_reject_url(leave.id), headers=auth_header(user_account)).status_code == 403


def test_worker_role_forbidden_on_both_routes(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    """Decision 18: a worker can never approve or reject their own (or any) leave."""
    federation, association = _make_federation_and_association(make_federation, make_association)
    worker_account, worker = _make_worker_account(
        make_account, make_worker, association_id=association.id
    )
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    assert client.post(_approve_url(leave.id), headers=auth_header(worker_account)).status_code == 403
    assert client.post(_reject_url(leave.id), headers=auth_header(worker_account)).status_code == 403


def test_federation_admin_forbidden_on_both_routes(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    """
    Decision 20: FEDERATION_ADMIN is not treated as ASSOCIATION_ADMIN here.
    `app/api/federation.py`'s own docstring already establishes federation
    admins never modify/allocate workers -- this is the same 403 every
    other ASSOCIATION_ADMIN-only route already gives a FEDERATION_ADMIN.
    """
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    assert client.post(_approve_url(leave.id), headers=auth_header(fed_admin)).status_code == 403
    assert client.post(_reject_url(leave.id), headers=auth_header(fed_admin)).status_code == 403


def test_unauthenticated_returns_401_on_both_routes(client):
    leave_id = uuid.uuid4()
    assert client.post(_approve_url(leave_id)).status_code == 401
    assert client.post(_reject_url(leave_id)).status_code == 401


def test_nonexistent_leave_returns_404(
    client, make_account, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    assert client.post(_approve_url(uuid.uuid4()), headers=auth_header(admin)).status_code == 404
    assert client.post(_reject_url(uuid.uuid4()), headers=auth_header(admin)).status_code == 404


# ============================================================= Approval ===


def test_approve_sets_reviewed_by_and_reviewed_at(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(admin))

    body = response.json()
    assert body["status"] == LeaveStatus.APPROVED.value
    assert body["reviewedBy"] == str(admin.id)
    assert body["reviewedAt"] is not None


def test_reject_sets_reviewed_by_and_reviewed_at(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_at_ist_days_ahead(3), end_at=_at_ist_days_ahead(5)
    )

    response = client.post(_reject_url(leave.id), headers=auth_header(admin))

    body = response.json()
    assert body["status"] == LeaveStatus.REJECTED.value
    assert body["reviewedBy"] == str(admin.id)
    assert body["reviewedAt"] is not None


def test_approved_leave_consumes_quota(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header, db_session,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(worker_id=worker.id, start_at=_ist(2026, 6, 1), end_at=_ist(2026, 6, 5))

    client.post(_approve_url(leave.id), headers=auth_header(admin))

    assert approved_leave_days_in_year(db_session, worker.id, 2026) == 5


def test_rejected_leave_does_not_consume_quota(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header, db_session,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(worker_id=worker.id, start_at=_ist(2026, 6, 1), end_at=_ist(2026, 6, 5))

    client.post(_reject_url(leave.id), headers=auth_header(admin))

    assert approved_leave_days_in_year(db_session, worker.id, 2026) == 0


# ===================================================== Invalid transitions ===


def test_approving_already_approved_leave_returns_409(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.APPROVED,
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 409


def test_approving_already_rejected_leave_returns_409(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.REJECTED,
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 409


def test_rejecting_already_approved_leave_returns_409(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.APPROVED,
    )

    response = client.post(_reject_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 409


def test_rejecting_already_rejected_leave_returns_409(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.REJECTED,
    )

    response = client.post(_reject_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 409


# ================================================================= Overlap ===


def test_approval_blocked_by_overlapping_pending_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    target = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 10, 10), end_at=_ist(2026, 10, 12)
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 11),
        end_at=_ist(2026, 10, 13),
        status=LeaveStatus.PENDING,
    )

    response = client.post(_approve_url(target.id), headers=auth_header(admin))

    assert response.status_code == 409


def test_approval_blocked_by_overlapping_approved_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    target = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 10, 10), end_at=_ist(2026, 10, 12)
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 11),
        end_at=_ist(2026, 10, 13),
        status=LeaveStatus.APPROVED,
    )

    response = client.post(_approve_url(target.id), headers=auth_header(admin))

    assert response.status_code == 409


def test_approval_not_blocked_by_overlapping_rejected_leave(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    target = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 10, 10), end_at=_ist(2026, 10, 12)
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 10, 11),
        end_at=_ist(2026, 10, 13),
        status=LeaveStatus.REJECTED,
    )

    response = client.post(_approve_url(target.id), headers=auth_header(admin))

    assert response.status_code == 200


# ========================================================= Assignment conflict ===


def test_approval_blocked_by_accepted_assignment(
    client, make_account, make_worker, make_federation, make_association,
    make_service, make_worker_skill, make_user_profile, make_service_request,
    make_assignment, make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)
    user_account = make_account(role=AccountRole.USER)
    user_profile = make_user_profile(account_id=user_account.id)

    service_request = make_service_request(
        user_id=user_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=_ist(2026, 10, 11, hour=14),
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.ACCEPTED,
    )
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 10, 10), end_at=_ist(2026, 10, 12)
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 409


def test_approval_not_blocked_by_non_accepted_assignment(
    client, make_account, make_worker, make_federation, make_association,
    make_service, make_worker_skill, make_user_profile, make_service_request,
    make_assignment, make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)
    user_account = make_account(role=AccountRole.USER)
    user_profile = make_user_profile(account_id=user_account.id)

    service_request = make_service_request(
        user_id=user_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=_ist(2026, 10, 11, hour=14),
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )
    leave = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 10, 10), end_at=_ist(2026, 10, 12)
    )

    response = client.post(_approve_url(leave.id), headers=auth_header(admin))

    assert response.status_code == 200


# ================================================================== Quota ===


def test_approval_at_exact_60_day_boundary_succeeds(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    # 59 already-approved days: 1 Jan - 28 Feb 2026 (31 + 28 = 59).
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 2, 28),
        status=LeaveStatus.APPROVED,
    )
    # A new 1-day PENDING leave bringing the total to exactly 60.
    new_leave = make_worker_leave(worker_id=worker.id, start_at=_ist(2026, 3, 1), end_at=_ist(2026, 3, 1))

    response = client.post(_approve_url(new_leave.id), headers=auth_header(admin))

    assert response.status_code == 200


def test_approval_beyond_60_day_boundary_fails_and_stays_pending(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header, db_session,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    # 60 already-approved days: 1 Jan - 1 Mar 2026 (31 + 28 + 1 = 60).
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 3, 1),
        status=LeaveStatus.APPROVED,
    )
    # One more day would be the 61st.
    new_leave = make_worker_leave(worker_id=worker.id, start_at=_ist(2026, 3, 2), end_at=_ist(2026, 3, 2))

    response = client.post(_approve_url(new_leave.id), headers=auth_header(admin))

    assert response.status_code == 409

    db_session.refresh(new_leave)
    assert new_leave.status == LeaveStatus.PENDING


def test_pending_leave_does_not_count_toward_quota_check(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    """A PENDING leave elsewhere for the same worker must not block approval via the quota check."""
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    # 60 days of PENDING (not approved) leave elsewhere in the year.
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 3, 1),
        status=LeaveStatus.PENDING,
    )
    new_leave = make_worker_leave(worker_id=worker.id, start_at=_ist(2026, 6, 1), end_at=_ist(2026, 6, 1))

    response = client.post(_approve_url(new_leave.id), headers=auth_header(admin))

    assert response.status_code == 200


def test_rejected_leave_does_not_count_toward_quota_check(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    # 60 days of REJECTED leave elsewhere in the year.
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 3, 1),
        status=LeaveStatus.REJECTED,
    )
    new_leave = make_worker_leave(worker_id=worker.id, start_at=_ist(2026, 6, 1), end_at=_ist(2026, 6, 1))

    response = client.post(_approve_url(new_leave.id), headers=auth_header(admin))

    assert response.status_code == 200


def test_cross_year_leave_quota_checked_in_both_years(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    """30 Dec -> 2 Jan splits as 2 days in the old year + 2 days in the new year; both must pass."""
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    new_leave = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 12, 30), end_at=_ist(2027, 1, 2)
    )

    response = client.post(_approve_url(new_leave.id), headers=auth_header(admin))

    assert response.status_code == 200


def test_cross_year_leave_blocked_when_one_affected_year_exceeds_quota(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header, db_session,
):
    """Decision 6: if ANY affected year would exceed 60, approval must fail -- even if the other year is fine."""
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    # 60 already-approved days in 2026: 1 Jan - 1 Mar.
    make_worker_leave(
        worker_id=worker.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 3, 1),
        status=LeaveStatus.APPROVED,
    )
    # This leave contributes 2 more days to the already-full 2026 (31 Dec,
    # 30 Dec) and 2 days to the otherwise-empty 2027 -- 2027 alone would
    # pass, but 2026 would be pushed to 62, so the whole approval fails.
    new_leave = make_worker_leave(
        worker_id=worker.id, start_at=_ist(2026, 12, 30), end_at=_ist(2027, 1, 2)
    )

    response = client.post(_approve_url(new_leave.id), headers=auth_header(admin))

    assert response.status_code == 409

    db_session.refresh(new_leave)
    assert new_leave.status == LeaveStatus.PENDING


def test_different_workers_quotas_are_independent(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    _, worker_a = _make_worker_account(make_account, make_worker, association_id=association.id)
    _, worker_b = _make_worker_account(make_account, make_worker, association_id=association.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    # worker_a is already at the 60-day cap.
    make_worker_leave(
        worker_id=worker_a.id,
        start_at=_ist(2026, 1, 1),
        end_at=_ist(2026, 3, 1),
        status=LeaveStatus.APPROVED,
    )
    # worker_b has no approved leave at all -- their own 1-day request
    # must succeed regardless of worker_a's exhausted quota.
    worker_b_leave = make_worker_leave(
        worker_id=worker_b.id, start_at=_ist(2026, 3, 2), end_at=_ist(2026, 3, 2)
    )

    response = client.post(_approve_url(worker_b_leave.id), headers=auth_header(admin))

    assert response.status_code == 200
