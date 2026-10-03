"""
Tests for the Phase 7C-D WORKER leave routes:
`POST /workers/me/leaves`, `GET /workers/me/leaves`.

Mirrors `tests/test_workers.py`'s exact structural conventions (local
helpers, `set(body.keys())` shape pinning, explicit 401/403-per-role
loops). This file tests the HTTP-level routes only -- the pure business-
rule primitives these routes call (`leave_overlaps_existing`,
`leave_conflicts_accepted_assignment`, etc.) are already tested directly
in `tests/test_worker_leave_rules.py` and are not re-tested here, and the
`WorkerLeave` model itself is already tested in
`tests/test_worker_leave_model.py`.
"""

import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.enums import AccountRole, AssignmentStatus
from app.models.worker_leave import LeaveStatus

LEAVES_URL = "/workers/me/leaves"

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def _at_ist_days_ahead(days_ahead: int, hour: int = 12) -> datetime:
    """
    A timezone-aware UTC datetime whose Asia/Kolkata calendar date is
    exactly `days_ahead` Asia/Kolkata calendar days after today's
    Asia/Kolkata calendar date, at `hour` IST. Mirrors
    `tests/test_requests.py`'s identical helper for the Phase 7C-C
    booking-horizon tests -- the same calendar-day boundary mechanics
    apply here for the 2-day minimum notice period.
    """
    today_ist = datetime.now(KOLKATA_TZ).date()
    target_date = today_ist + timedelta(days=days_ahead)
    target_ist = datetime.combine(target_date, time(hour=hour), tzinfo=KOLKATA_TZ)
    return target_ist.astimezone(timezone.utc)


def _make_federation_and_association(make_federation, make_association):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    return federation, association


def _make_worker_account(make_account, make_worker, *, association_id, full_name="Test Worker"):
    account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=account.id, association_id=association_id, full_name=full_name)
    return account, worker


def _leave_payload(*, days_ahead=3, duration_days=1) -> dict:
    start = _at_ist_days_ahead(days_ahead)
    end = start + timedelta(days=duration_days - 1)
    return {"startAt": start.isoformat(), "endAt": end.isoformat()}


# =================================================== POST /workers/me/leaves ===


def test_worker_can_submit_leave_returns_201(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    response = client.post(LEAVES_URL, headers=auth_header(account), json=_leave_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["workerId"] == str(worker.id)
    assert body["status"] == LeaveStatus.PENDING.value
    assert body["reviewedBy"] is None
    assert body["reviewedAt"] is None
    assert set(body.keys()) == {
        "id",
        "workerId",
        "startAt",
        "endAt",
        "status",
        "reviewedBy",
        "reviewedAt",
        "createdAt",
        "updatedAt",
    }


def test_submit_leave_exactly_2_days_notice_accepted(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    response = client.post(
        LEAVES_URL, headers=auth_header(account), json=_leave_payload(days_ahead=2)
    )

    assert response.status_code == 201


def test_submit_leave_insufficient_notice_rejected(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    response = client.post(
        LEAVES_URL, headers=auth_header(account), json=_leave_payload(days_ahead=1)
    )

    assert response.status_code == 422


def test_submit_leave_same_day_start_end_is_valid_1_day_leave(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    """
    A same-Asia/Kolkata-calendar-day leave (startAt == endAt's calendar
    date) is a valid 1-day leave -- the minimum-duration rule is already
    satisfied automatically by inclusive day-counting (see the Phase 7C-D
    investigation's own finding), so this needs no special-case rejection.
    """
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    start = _at_ist_days_ahead(3, hour=9)
    end = _at_ist_days_ahead(3, hour=18)
    payload = {"startAt": start.isoformat(), "endAt": end.isoformat()}

    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 201


def test_submit_leave_end_before_start_rejected(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    start = _at_ist_days_ahead(5)
    end = _at_ist_days_ahead(3)
    payload = {"startAt": start.isoformat(), "endAt": end.isoformat()}

    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 422


def test_submit_leave_naive_datetime_rejected(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    payload = _leave_payload()
    naive_start = datetime.now() + timedelta(days=3)
    payload["startAt"] = naive_start.isoformat()  # no offset/'Z'

    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 422


def test_submit_leave_overlapping_pending_rejected(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.PENDING,
    )

    payload = {
        "startAt": _at_ist_days_ahead(4).isoformat(),
        "endAt": _at_ist_days_ahead(6).isoformat(),
    }
    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 409


def test_submit_leave_overlapping_approved_rejected(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.APPROVED,
    )

    payload = {
        "startAt": _at_ist_days_ahead(4).isoformat(),
        "endAt": _at_ist_days_ahead(6).isoformat(),
    }
    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 409


def test_submit_leave_overlapping_rejected_leave_allowed(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.REJECTED,
    )

    payload = {
        "startAt": _at_ist_days_ahead(4).isoformat(),
        "endAt": _at_ist_days_ahead(6).isoformat(),
    }
    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 201


def test_submit_leave_conflicting_accepted_assignment_rejected(
    client, make_account, make_worker, make_federation, make_association,
    make_service, make_worker_skill, make_user_profile, make_service_request,
    make_assignment, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)
    user_account = make_account(role=AccountRole.USER)
    user_profile = make_user_profile(account_id=user_account.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    service_request = make_service_request(
        user_id=user_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=_at_ist_days_ahead(4, hour=14),
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.ACCEPTED,
    )

    payload = {
        "startAt": _at_ist_days_ahead(3).isoformat(),
        "endAt": _at_ist_days_ahead(5).isoformat(),
    }
    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 409


def test_submit_leave_different_worker_overlap_does_not_conflict(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account_a, worker_a = _make_worker_account(make_account, make_worker, association_id=association.id)
    account_b, worker_b = _make_worker_account(make_account, make_worker, association_id=association.id)

    make_worker_leave(
        worker_id=worker_a.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.APPROVED,
    )

    payload = {
        "startAt": _at_ist_days_ahead(3).isoformat(),
        "endAt": _at_ist_days_ahead(5).isoformat(),
    }
    response = client.post(LEAVES_URL, headers=auth_header(account_b), json=payload)

    assert response.status_code == 201


def test_submit_leave_unauthenticated_returns_401(client):
    assert client.post(LEAVES_URL, json=_leave_payload()).status_code == 401


def test_submit_leave_wrong_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert (
        client.post(LEAVES_URL, headers=auth_header(user_account), json=_leave_payload()).status_code
        == 403
    )

    assoc_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assert (
        client.post(LEAVES_URL, headers=auth_header(assoc_admin), json=_leave_payload()).status_code
        == 403
    )

    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    assert (
        client.post(LEAVES_URL, headers=auth_header(fed_admin), json=_leave_payload()).status_code
        == 403
    )


def test_submit_leave_without_worker_profile_returns_404(client, make_account, auth_header):
    account = make_account(role=AccountRole.WORKER)
    response = client.post(LEAVES_URL, headers=auth_header(account), json=_leave_payload())
    assert response.status_code == 404


def test_submit_leave_rejects_client_supplied_worker_id_field(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    """`extra="forbid"` rejects any field beyond startAt/endAt, including an attempted workerId."""
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    payload = _leave_payload()
    payload["workerId"] = str(uuid.uuid4())

    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 422


def test_submit_leave_rejects_client_supplied_status_field(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, _ = _make_worker_account(make_account, make_worker, association_id=association.id)

    payload = _leave_payload()
    payload["status"] = "APPROVED"

    response = client.post(LEAVES_URL, headers=auth_header(account), json=payload)

    assert response.status_code == 422


# ===================================================== GET /workers/me/leaves ===


def test_worker_can_list_own_leaves_returns_200(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    leave = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(5),
        status=LeaveStatus.PENDING,
    )

    response = client.get(LEAVES_URL, headers=auth_header(account))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == str(leave.id)
    assert item["status"] == LeaveStatus.PENDING.value
    assert set(item.keys()) == {
        "id",
        "workerId",
        "startAt",
        "endAt",
        "status",
        "reviewedBy",
        "reviewedAt",
        "createdAt",
        "updatedAt",
    }


def test_leaves_list_includes_every_status(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(4),
        status=LeaveStatus.PENDING,
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(10),
        end_at=_at_ist_days_ahead(11),
        status=LeaveStatus.APPROVED,
    )
    make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(20),
        end_at=_at_ist_days_ahead(21),
        status=LeaveStatus.REJECTED,
    )

    response = client.get(LEAVES_URL, headers=auth_header(account))

    assert response.json()["total"] == 3


def test_leaves_list_ordering_is_deterministic(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header, db_session,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    leave_one = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(4),
        status=LeaveStatus.PENDING,
    )
    leave_two = make_worker_leave(
        worker_id=worker.id,
        start_at=_at_ist_days_ahead(10),
        end_at=_at_ist_days_ahead(11),
        status=LeaveStatus.PENDING,
    )

    # Force identical `created_at` so the `id DESC` tiebreaker is what's
    # actually under test, mirroring
    # `test_assignments_list_ordering_is_deterministic`'s own approach.
    same_instant = datetime.now(timezone.utc)
    leave_one.created_at = same_instant
    leave_two.created_at = same_instant
    db_session.flush()

    response = client.get(LEAVES_URL, headers=auth_header(account))

    ids_in_order = [item["id"] for item in response.json()["items"]]
    expected_order = sorted([str(leave_one.id), str(leave_two.id)], reverse=True)
    assert ids_in_order == expected_order


def test_worker_does_not_see_other_worker_leaves(
    client, make_account, make_worker, make_federation, make_association,
    make_worker_leave, auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account_a, worker_a = _make_worker_account(make_account, make_worker, association_id=association.id)
    account_b, worker_b = _make_worker_account(make_account, make_worker, association_id=association.id)

    make_worker_leave(
        worker_id=worker_b.id,
        start_at=_at_ist_days_ahead(3),
        end_at=_at_ist_days_ahead(4),
        status=LeaveStatus.PENDING,
    )

    response = client.get(LEAVES_URL, headers=auth_header(account_a))

    assert response.json()["total"] == 0


def test_list_leaves_unauthenticated_returns_401(client):
    assert client.get(LEAVES_URL).status_code == 401


def test_list_leaves_wrong_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(LEAVES_URL, headers=auth_header(user_account)).status_code == 403

    assoc_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assert client.get(LEAVES_URL, headers=auth_header(assoc_admin)).status_code == 403

    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    assert client.get(LEAVES_URL, headers=auth_header(fed_admin)).status_code == 403


def test_list_leaves_without_worker_profile_returns_404(client, make_account, auth_header):
    account = make_account(role=AccountRole.WORKER)
    response = client.get(LEAVES_URL, headers=auth_header(account))
    assert response.status_code == 404
