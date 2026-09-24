"""
Tests for the Phase 5E-D WORKER routes:
`GET /workers/me`, `GET /workers/me/assignments`.
"""

from app.models.enums import AccountRole, AssignmentStatus

ME_URL = "/workers/me"
ASSIGNMENTS_URL = "/workers/me/assignments"


def _make_federation_and_association(make_federation, make_association):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    return federation, association


def _make_worker_account(make_account, make_worker, *, association_id, full_name="Test Worker"):
    account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=account.id, association_id=association_id, full_name=full_name)
    return account, worker


# --- GET /workers/me ------------------------------------------------------


def test_worker_can_get_own_profile(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(
        make_account, make_worker, association_id=association.id, full_name="Mukesh Yadav"
    )

    response = client.get(ME_URL, headers=auth_header(account))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(worker.id)
    assert body["fullName"] == "Mukesh Yadav"
    assert body["associationId"] == str(association.id)
    assert set(body.keys()) == {
        "id",
        "accountId",
        "associationId",
        "workerCode",
        "fullName",
        "phoneNumber",
        "status",
        "address",
        "pincode",
        "rating",
        "totalJobsCompleted",
        "createdAt",
        "updatedAt",
    }


def test_worker_without_profile_returns_404(client, make_account, auth_header):
    account = make_account(role=AccountRole.WORKER)
    response = client.get(ME_URL, headers=auth_header(account))
    assert response.status_code == 404


def test_worker_me_unauthenticated_returns_401(client):
    assert client.get(ME_URL).status_code == 401


def test_worker_me_wrong_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(ME_URL, headers=auth_header(user_account)).status_code == 403

    assoc_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assert client.get(ME_URL, headers=auth_header(assoc_admin)).status_code == 403

    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    assert client.get(ME_URL, headers=auth_header(fed_admin)).status_code == 403


def test_worker_me_password_hash_never_returned(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account = make_account(role=AccountRole.WORKER, password="secret123")
    make_worker(account_id=account.id, association_id=association.id)

    response = client.get(ME_URL, headers=auth_header(account))
    assert "password" not in response.text.lower()


# --- GET /workers/me/assignments ------------------------------------------


def test_worker_can_list_own_assignments(
    client,
    make_account,
    make_worker,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    make_assignment,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assignment = make_assignment(
        request_id=service_request.id, worker_id=worker.id, assigned_by=admin.id
    )

    response = client.get(ASSIGNMENTS_URL, headers=auth_header(account))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == str(assignment.id)
    assert item["status"] == AssignmentStatus.PENDING_RESPONSE.value
    assert "createdAt" not in item
    assert set(item.keys()) == {
        "id",
        "requestId",
        "workerId",
        "assignedBy",
        "status",
        "assignedAt",
        "respondedAt",
        "updatedAt",
    }


def test_worker_does_not_see_other_worker_assignments(
    client,
    make_account,
    make_worker,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    make_assignment,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account_a, worker_a = _make_worker_account(make_account, make_worker, association_id=association.id)
    account_b, worker_b = _make_worker_account(make_account, make_worker, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    make_assignment(request_id=service_request.id, worker_id=worker_b.id, assigned_by=admin.id)

    response = client.get(ASSIGNMENTS_URL, headers=auth_header(account_a))
    assert response.json()["total"] == 0


def test_assignments_list_ordering_is_deterministic(
    client,
    make_account,
    make_worker,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    make_assignment,
    auth_header,
    db_session,
):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import update as sa_update

    from app.models.assignment import Assignment

    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    older = make_assignment(request_id=service_request.id, worker_id=worker.id, assigned_by=admin.id)
    newer = make_assignment(request_id=service_request.id, worker_id=worker.id, assigned_by=admin.id)

    now = datetime.now(timezone.utc)
    db_session.execute(
        sa_update(Assignment).where(Assignment.id == older.id).values(assigned_at=now - timedelta(minutes=10))
    )
    db_session.execute(
        sa_update(Assignment).where(Assignment.id == newer.id).values(assigned_at=now)
    )
    db_session.flush()

    response = client.get(ASSIGNMENTS_URL, headers=auth_header(account))
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(newer.id), str(older.id)]


def test_assignments_list_pagination(
    client,
    make_account,
    make_worker,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    make_assignment,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    for _ in range(3):
        make_assignment(request_id=service_request.id, worker_id=worker.id, assigned_by=admin.id)

    response = client.get(
        ASSIGNMENTS_URL, params={"page": 1, "page_size": 2}, headers=auth_header(account)
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_assignments_list_empty_result(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    response = client.get(ASSIGNMENTS_URL, headers=auth_header(account))
    assert response.json()["total"] == 0


def test_assignments_list_malformed_pagination_returns_422(
    client, make_account, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    response = client.get(ASSIGNMENTS_URL, params={"page": -1}, headers=auth_header(account))
    assert response.status_code == 422


def test_assignments_list_unauthenticated_returns_401(client):
    assert client.get(ASSIGNMENTS_URL).status_code == 401


def test_assignments_list_wrong_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(ASSIGNMENTS_URL, headers=auth_header(user_account)).status_code == 403

    assoc_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assert client.get(ASSIGNMENTS_URL, headers=auth_header(assoc_admin)).status_code == 403

    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    assert client.get(ASSIGNMENTS_URL, headers=auth_header(fed_admin)).status_code == 403


def test_worker_id_query_param_cannot_bypass_scope(
    client,
    make_account,
    make_worker,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    make_assignment,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account_a, worker_a = _make_worker_account(make_account, make_worker, association_id=association.id)
    account_b, worker_b = _make_worker_account(make_account, make_worker, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    make_assignment(request_id=service_request.id, worker_id=worker_b.id, assigned_by=admin.id)

    response = client.get(
        ASSIGNMENTS_URL, params={"workerId": str(worker_b.id)}, headers=auth_header(account_a)
    )
    assert response.json()["total"] == 0


def test_read_apis_do_not_mutate_assignment(
    client,
    make_account,
    make_worker,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    make_assignment,
    auth_header,
    db_session,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    account, worker = _make_worker_account(make_account, make_worker, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assignment = make_assignment(request_id=service_request.id, worker_id=worker.id, assigned_by=admin.id)
    original_status = assignment.status
    original_updated_at = assignment.updated_at

    client.get(ASSIGNMENTS_URL, headers=auth_header(account))

    db_session.refresh(assignment)
    assert assignment.status == original_status
    assert assignment.updated_at == original_updated_at
