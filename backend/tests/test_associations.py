"""
Tests for the Phase 5E-D ASSOCIATION_ADMIN routes:
`GET /associations/me/workers`, `GET /associations/me/requests`,
`GET /associations/me/requests/{request_id}`.
"""

import uuid

from sqlalchemy import update as sa_update

from app.models.enums import AccountRole
from app.models.service_request import ServiceRequest

WORKERS_URL = "/associations/me/workers"
REQUESTS_URL = "/associations/me/requests"


def _make_association_admin(make_account, *, association_id):
    return make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association_id)


def _make_federation_and_association(make_federation, make_association):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    return federation, association


# --- GET /associations/me/workers ---------------------------------------


def test_admin_can_list_own_association_workers(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(
        account_id=worker_account.id, association_id=association.id, full_name="Amit Kumar"
    )

    response = client.get(WORKERS_URL, headers=auth_header(admin))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["fullName"] == "Amit Kumar"
    assert item["associationId"] == str(association.id)
    assert set(item.keys()) == {
        "id",
        "accountId",
        "associationId",
        "workerCode",
        "fullName",
        "phoneNumber",
        "status",
        "createdAt",
        "updatedAt",
    }


def test_admin_does_not_see_other_association_workers(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation, association_a = _make_federation_and_association(make_federation, make_association)
    association_b = make_association(federation_id=federation.id)
    admin_a = _make_association_admin(make_account, association_id=association_a.id)

    worker_account_b = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account_b.id, association_id=association_b.id)

    response = client.get(WORKERS_URL, headers=auth_header(admin_a))

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_workers_list_ordering_is_deterministic(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    for name in ["Zara", "Amit", "Mohan"]:
        worker_account = make_account(role=AccountRole.WORKER)
        make_worker(account_id=worker_account.id, association_id=association.id, full_name=name)

    response = client.get(WORKERS_URL, headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert names == sorted(names)


def test_workers_list_pagination(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    for i in range(5):
        worker_account = make_account(role=AccountRole.WORKER)
        make_worker(
            account_id=worker_account.id, association_id=association.id, full_name=f"Worker {i}"
        )

    response = client.get(WORKERS_URL, params={"page": 2, "page_size": 2}, headers=auth_header(admin))
    body = response.json()
    assert body["page"] == 2
    assert body["pageSize"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_workers_list_empty_result(
    client, make_account, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    response = client.get(WORKERS_URL, headers=auth_header(admin))
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_workers_list_malformed_pagination_returns_422(
    client, make_account, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    response = client.get(WORKERS_URL, params={"page": 0}, headers=auth_header(admin))
    assert response.status_code == 422


def test_workers_list_unauthenticated_returns_401(client):
    response = client.get(WORKERS_URL)
    assert response.status_code == 401


def test_workers_list_wrong_role_forbidden(
    client, make_account, make_user_profile, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(WORKERS_URL, headers=auth_header(user_account)).status_code == 403

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id)
    assert client.get(WORKERS_URL, headers=auth_header(worker_account)).status_code == 403

    federation_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    assert client.get(WORKERS_URL, headers=auth_header(federation_admin)).status_code == 403


def test_workers_list_missing_association_returns_404(client, make_account, auth_header):
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=None)
    response = client.get(WORKERS_URL, headers=auth_header(admin))
    assert response.status_code == 404


def test_workers_password_hash_never_returned(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    worker_account = make_account(role=AccountRole.WORKER, password="secret123")
    make_worker(account_id=worker_account.id, association_id=association.id)

    response = client.get(WORKERS_URL, headers=auth_header(admin))
    body_text = response.text
    assert "password" not in body_text.lower()


# --- GET /associations/me/requests --------------------------------------


def test_admin_can_list_own_association_requests(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    make_service_request(user_id=profile.id, service_id=service.id, association_id=association.id)

    response = client.get(REQUESTS_URL, headers=auth_header(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["associationId"] == str(association.id)
    assert "userId" not in item
    assert "workerId" not in item


def test_admin_does_not_see_other_association_requests(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
):
    federation, association_a = _make_federation_and_association(make_federation, make_association)
    association_b = make_association(federation_id=federation.id)
    admin_a = _make_association_admin(make_account, association_id=association_a.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    make_service_request(user_id=profile.id, service_id=service.id, association_id=association_b.id)

    response = client.get(REQUESTS_URL, headers=auth_header(admin_a))
    assert response.json()["total"] == 0


def test_requests_list_ordering_is_newest_first(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
    db_session,
):
    from datetime import datetime, timedelta, timezone

    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()

    older = make_service_request(user_id=profile.id, service_id=service.id, association_id=association.id)
    newer = make_service_request(user_id=profile.id, service_id=service.id, association_id=association.id)

    now = datetime.now(timezone.utc)
    db_session.execute(
        sa_update(ServiceRequest).where(ServiceRequest.id == older.id).values(created_at=now - timedelta(minutes=10))
    )
    db_session.execute(
        sa_update(ServiceRequest).where(ServiceRequest.id == newer.id).values(created_at=now)
    )
    db_session.flush()

    response = client.get(REQUESTS_URL, headers=auth_header(admin))
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(newer.id), str(older.id)]


def test_requests_list_pagination(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    for _ in range(3):
        make_service_request(user_id=profile.id, service_id=service.id, association_id=association.id)

    response = client.get(REQUESTS_URL, params={"page": 1, "page_size": 2}, headers=auth_header(admin))
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_requests_list_empty_result(
    client, make_account, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    response = client.get(REQUESTS_URL, headers=auth_header(admin))
    assert response.json()["total"] == 0


def test_requests_list_unauthenticated_returns_401(client):
    assert client.get(REQUESTS_URL).status_code == 401


def test_requests_list_wrong_role_forbidden(
    client, make_account, make_user_profile, make_worker, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(REQUESTS_URL, headers=auth_header(user_account)).status_code == 403

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id)
    assert client.get(REQUESTS_URL, headers=auth_header(worker_account)).status_code == 403

    federation_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    assert client.get(REQUESTS_URL, headers=auth_header(federation_admin)).status_code == 403


# --- GET /associations/me/requests/{request_id} -------------------------


def test_admin_can_get_own_association_request(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )

    response = client.get(f"{REQUESTS_URL}/{service_request.id}", headers=auth_header(admin))
    assert response.status_code == 200
    assert response.json()["id"] == str(service_request.id)


def test_get_request_from_other_association_returns_404(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
):
    federation, association_a = _make_federation_and_association(make_federation, make_association)
    association_b = make_association(federation_id=federation.id)
    admin_a = _make_association_admin(make_account, association_id=association_a.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association_b.id
    )

    response = client.get(f"{REQUESTS_URL}/{service_request.id}", headers=auth_header(admin_a))
    assert response.status_code == 404


def test_get_nonexistent_request_returns_404(
    client, make_account, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    response = client.get(f"{REQUESTS_URL}/{uuid.uuid4()}", headers=auth_header(admin))
    assert response.status_code == 404


def test_get_request_malformed_uuid_returns_422(
    client, make_account, make_federation, make_association, auth_header
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    response = client.get(f"{REQUESTS_URL}/not-a-uuid", headers=auth_header(admin))
    assert response.status_code == 422


def test_association_id_query_param_cannot_bypass_scope(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
):
    """An extra/ignored `associationId` query param must not widen scope."""
    federation, association_a = _make_federation_and_association(make_federation, make_association)
    association_b = make_association(federation_id=federation.id)
    admin_a = _make_association_admin(make_account, association_id=association_a.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    make_service_request(user_id=profile.id, service_id=service.id, association_id=association_b.id)

    response = client.get(
        REQUESTS_URL, params={"associationId": str(association_b.id)}, headers=auth_header(admin_a)
    )
    assert response.json()["total"] == 0


def test_read_apis_do_not_mutate_service_request(
    client,
    make_account,
    make_federation,
    make_association,
    make_service,
    make_user_profile,
    make_service_request,
    auth_header,
    db_session,
):
    federation, association = _make_federation_and_association(make_federation, make_association)
    admin = _make_association_admin(make_account, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id, service_id=service.id, association_id=association.id
    )
    original_status = service_request.status
    original_updated_at = service_request.updated_at

    client.get(f"{REQUESTS_URL}/{service_request.id}", headers=auth_header(admin))

    db_session.refresh(service_request)
    assert service_request.status == original_status
    assert service_request.updated_at == original_updated_at
