"""
Tests for the Phase 5E-J user cancellation endpoint:
`POST /requests/{request_id}/cancel` — USER, ServiceRequest
{PENDING, MATCHING, ASSIGNED, ACCEPTED} -> CANCELLED_BY_USER.

Covers authorization, the anti-enumeration 404 convention, every valid
starting status, every invalid (409) starting status, Assignment-history
preservation (including an ACCEPTED assignment left completely
untouched), repeated cancellation, and that the existing user/association
read APIs naturally surface CANCELLED_BY_USER once it happens.
"""

from datetime import datetime, timezone

import pytest

from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus

CANCEL_URL = "/requests/{request_id}/cancel"
OWN_REQUEST_URL = "/requests/{request_id}"
ASSOCIATION_REQUEST_URL = "/associations/me/requests/{request_id}"

REQUEST_DATETIME = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)


def _cancel_url(request_id) -> str:
    return CANCEL_URL.format(request_id=request_id)


def _build_request(
    make_federation,
    make_association,
    make_account,
    make_user_profile,
    make_service,
    make_service_request,
    *,
    status: ServiceRequestStatus = ServiceRequestStatus.PENDING,
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)

    service_request = make_service_request(
        user_id=profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
        status=status,
    )

    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    return {
        "federation": federation,
        "association": association,
        "service": service,
        "user_account": user_account,
        "profile": profile,
        "service_request": service_request,
        "admin": admin,
    }


# ===================================================== AUTHORIZATION ===


def test_unauthenticated_returns_401(client):
    import uuid

    response = client.post(_cancel_url(uuid.uuid4()))
    assert response.status_code == 401


def test_non_user_role_returns_403(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, auth_header,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )

    response = client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["admin"]))
    assert response.status_code == 403

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=ctx["association"].id)
    response = client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(worker_account))
    assert response.status_code == 403

    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=ctx["federation"].id)
    response = client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(fed_admin))
    assert response.status_code == 403


def test_nonexistent_request_returns_404(client, make_account, auth_header):
    import uuid

    user_account = make_account(role=AccountRole.USER)
    response = client.post(_cancel_url(uuid.uuid4()), headers=auth_header(user_account))
    assert response.status_code == 404


def test_cannot_cancel_another_users_request(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    other_user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=other_user_account.id)

    response = client.post(
        _cancel_url(ctx["service_request"].id), headers=auth_header(other_user_account)
    )
    assert response.status_code == 404


# ==================================================== VALID TRANSITIONS ===


@pytest.mark.parametrize(
    "starting_status",
    [
        ServiceRequestStatus.PENDING,
        ServiceRequestStatus.MATCHING,
        ServiceRequestStatus.ASSIGNED,
        ServiceRequestStatus.ACCEPTED,
    ],
)
def test_valid_starting_states_transition_to_cancelled_by_user(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header, db_session, starting_status,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=starting_status,
    )
    response = client.post(
        _cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(ctx["service_request"].id)
    assert body["status"] == ServiceRequestStatus.CANCELLED_BY_USER.value

    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.CANCELLED_BY_USER


# ================================================== INVALID (409) STATES ===


@pytest.mark.parametrize(
    "invalid_status",
    [
        ServiceRequestStatus.WORKER_COMPLETED,
        ServiceRequestStatus.USER_CONFIRMED,
        ServiceRequestStatus.PAYMENT_PENDING,
        ServiceRequestStatus.PAID,
        ServiceRequestStatus.COMPLETED,
        ServiceRequestStatus.CANCELLED_BY_USER,
    ],
)
def test_invalid_starting_states_return_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header, invalid_status,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=invalid_status,
    )
    response = client.post(
        _cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 409


def test_repeated_cancellation_is_rejected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.PENDING,
    )
    first = client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))
    assert first.status_code == 200

    second = client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))
    assert second.status_code == 409


# ==================================================== ASSIGNMENT HISTORY ===


def test_cancellation_with_no_assignment(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header, db_session,
):
    from sqlalchemy import select

    from app.models.assignment import Assignment

    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.PENDING,
    )
    response = client.post(
        _cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 200

    remaining = db_session.execute(
        select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
    ).scalars().all()
    assert remaining == []


def test_cancellation_with_an_accepted_assignment_leaves_it_untouched(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ACCEPTED,
    )
    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=ctx["association"].id)
    assignment = make_assignment(
        request_id=ctx["service_request"].id,
        worker_id=worker.id,
        assigned_by=ctx["admin"].id,
        status=AssignmentStatus.ACCEPTED,
    )
    original_worker_id = assignment.worker_id
    original_assigned_at = assignment.assigned_at
    original_responded_at = assignment.responded_at
    original_updated_at = assignment.updated_at

    response = client.post(
        _cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == ServiceRequestStatus.CANCELLED_BY_USER.value

    db_session.refresh(ctx["service_request"])
    db_session.refresh(assignment)
    assert ctx["service_request"].status == ServiceRequestStatus.CANCELLED_BY_USER
    # The critical assertion from the spec: Assignment.status stays
    # ACCEPTED -- it must NOT become CANCELLED_BY_WORKER or anything else.
    assert assignment.status == AssignmentStatus.ACCEPTED
    assert assignment.worker_id == original_worker_id
    assert assignment.assigned_at == original_assigned_at
    assert assignment.responded_at == original_responded_at
    assert assignment.updated_at == original_updated_at


def test_multiple_historical_assignments_are_preserved(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    """
    Assignment #1 -> Worker A -> DECLINED
    Assignment #2 -> Worker B -> CANCELLED_BY_WORKER
    Assignment #3 -> Worker C -> ACCEPTED
    After user cancellation, all three rows must remain exactly as they
    were, and no fourth Assignment is created.
    """
    from sqlalchemy import select

    from app.models.assignment import Assignment

    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ACCEPTED,
    )

    def _worker():
        account = make_account(role=AccountRole.WORKER)
        return make_worker(account_id=account.id, association_id=ctx["association"].id)

    worker_a = _worker()
    worker_b = _worker()
    worker_c = _worker()

    assignment_1 = make_assignment(
        request_id=ctx["service_request"].id, worker_id=worker_a.id,
        assigned_by=ctx["admin"].id, status=AssignmentStatus.DECLINED,
    )
    assignment_2 = make_assignment(
        request_id=ctx["service_request"].id, worker_id=worker_b.id,
        assigned_by=ctx["admin"].id, status=AssignmentStatus.CANCELLED_BY_WORKER,
    )
    assignment_3 = make_assignment(
        request_id=ctx["service_request"].id, worker_id=worker_c.id,
        assigned_by=ctx["admin"].id, status=AssignmentStatus.ACCEPTED,
    )

    snapshot = {
        assignment_1.id: (assignment_1.status, assignment_1.worker_id),
        assignment_2.id: (assignment_2.status, assignment_2.worker_id),
        assignment_3.id: (assignment_3.status, assignment_3.worker_id),
    }

    response = client.post(
        _cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 200

    remaining = db_session.execute(
        select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
    ).scalars().all()
    assert len(remaining) == 3
    for row in remaining:
        assert snapshot[row.id] == (row.status, row.worker_id)


def test_no_new_assignment_is_created(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    from sqlalchemy import select

    from app.models.assignment import Assignment

    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ASSIGNED,
    )
    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=ctx["association"].id)
    make_assignment(
        request_id=ctx["service_request"].id,
        worker_id=worker.id,
        assigned_by=ctx["admin"].id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )

    before_count = len(
        db_session.execute(
            select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
        ).scalars().all()
    )
    client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))
    after_count = len(
        db_session.execute(
            select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
        ).scalars().all()
    )
    assert after_count == before_count == 1


# ==================================================== EXISTING READ APIs ===


def test_own_request_read_api_shows_cancelled_by_user(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.PENDING,
    )
    client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))

    response = client.get(
        OWN_REQUEST_URL.format(request_id=ctx["service_request"].id),
        headers=auth_header(ctx["user_account"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == ServiceRequestStatus.CANCELLED_BY_USER.value


def test_association_admin_read_api_shows_cancelled_by_user(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.PENDING,
    )
    client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))

    response = client.get(
        ASSOCIATION_REQUEST_URL.format(request_id=ctx["service_request"].id),
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == ServiceRequestStatus.CANCELLED_BY_USER.value


def test_worker_assignment_visibility_preserved_after_cancellation(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ACCEPTED,
    )
    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=ctx["association"].id)
    assignment = make_assignment(
        request_id=ctx["service_request"].id,
        worker_id=worker.id,
        assigned_by=ctx["admin"].id,
        status=AssignmentStatus.ACCEPTED,
    )

    client.post(_cancel_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))

    response = client.get("/workers/me/assignments", headers=auth_header(worker_account))
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(assignment.id)
    assert items[0]["status"] == AssignmentStatus.ACCEPTED.value


# ========================================================== REGRESSION ===


def test_existing_accept_flow_unaffected_by_cancel_endpoint(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ASSIGNED,
    )
    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=ctx["association"].id)
    assignment = make_assignment(
        request_id=ctx["service_request"].id,
        worker_id=worker.id,
        assigned_by=ctx["admin"].id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )

    response = client.post(f"/assignments/{assignment.id}/accept", headers=auth_header(worker_account))
    assert response.status_code == 200
    assert response.json()["status"] == AssignmentStatus.ACCEPTED.value

    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.ACCEPTED
