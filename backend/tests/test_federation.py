"""
Tests for the Phase 5E-D FEDERATION_ADMIN routes:
`GET /federation/me/associations`, `GET /federation/me/workers`.
"""

from app.models.enums import AccountRole

ASSOCIATIONS_URL = "/federation/me/associations"
WORKERS_URL = "/federation/me/workers"


def _make_federation_admin(make_account, *, federation_id):
    return make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation_id)


# --- GET /federation/me/associations --------------------------------------


def test_federation_admin_can_list_own_associations(
    client, make_account, make_federation, make_association, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id, name="Zeta Association")
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    response = client.get(ASSOCIATIONS_URL, headers=auth_header(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == str(association.id)
    assert item["federationId"] == str(federation.id)
    assert set(item.keys()) == {"id", "federationId", "name", "createdAt", "updatedAt"}


def test_federation_admin_does_not_see_other_federation_associations(
    client, make_account, make_federation, make_association, auth_header
):
    federation_a = make_federation()
    federation_b = make_federation()
    make_association(federation_id=federation_b.id)
    admin_a = _make_federation_admin(make_account, federation_id=federation_a.id)

    response = client.get(ASSOCIATIONS_URL, headers=auth_header(admin_a))
    assert response.json()["total"] == 0


def test_associations_list_ordering_is_deterministic(
    client, make_account, make_federation, make_association, auth_header
):
    federation = make_federation()
    for name in ["Zeta", "Alpha", "Mango"]:
        make_association(federation_id=federation.id, name=name)
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    response = client.get(ASSOCIATIONS_URL, headers=auth_header(admin))
    names = [item["name"] for item in response.json()["items"]]
    assert names == sorted(names)


def test_associations_list_pagination(
    client, make_account, make_federation, make_association, auth_header
):
    federation = make_federation()
    for i in range(3):
        make_association(federation_id=federation.id, name=f"Association {i}")
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    response = client.get(
        ASSOCIATIONS_URL, params={"page": 1, "page_size": 2}, headers=auth_header(admin)
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_associations_list_empty_result(client, make_account, make_federation, auth_header):
    federation = make_federation()
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    response = client.get(ASSOCIATIONS_URL, headers=auth_header(admin))
    assert response.json()["total"] == 0


def test_associations_list_unauthenticated_returns_401(client):
    assert client.get(ASSOCIATIONS_URL).status_code == 401


def test_associations_list_wrong_role_forbidden(
    client, make_account, make_user_profile, make_worker, make_federation, make_association, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(ASSOCIATIONS_URL, headers=auth_header(user_account)).status_code == 403

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id)
    assert client.get(ASSOCIATIONS_URL, headers=auth_header(worker_account)).status_code == 403

    assoc_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assert client.get(ASSOCIATIONS_URL, headers=auth_header(assoc_admin)).status_code == 403


def test_associations_list_missing_federation_returns_404(client, make_account, auth_header):
    admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=None)
    response = client.get(ASSOCIATIONS_URL, headers=auth_header(admin))
    assert response.status_code == 404


# --- GET /federation/me/workers --------------------------------------------


def test_federation_admin_can_list_workers_under_federation(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id, full_name="Priya Singh")

    response = client.get(WORKERS_URL, headers=auth_header(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["fullName"] == "Priya Singh"
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


def test_federation_admin_does_not_see_workers_outside_federation(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation_a = make_federation()
    federation_b = make_federation()
    association_b = make_association(federation_id=federation_b.id)
    admin_a = _make_federation_admin(make_account, federation_id=federation_a.id)

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association_b.id)

    response = client.get(WORKERS_URL, headers=auth_header(admin_a))
    assert response.json()["total"] == 0


def test_workers_under_federation_ordering_is_deterministic(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    for name in ["Zara", "Amit", "Mohan"]:
        worker_account = make_account(role=AccountRole.WORKER)
        make_worker(account_id=worker_account.id, association_id=association.id, full_name=name)

    response = client.get(WORKERS_URL, headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert names == sorted(names)


def test_workers_under_federation_pagination(
    client, make_account, make_federation, make_association, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    for i in range(3):
        worker_account = make_account(role=AccountRole.WORKER)
        make_worker(
            account_id=worker_account.id, association_id=association.id, full_name=f"Worker {i}"
        )

    response = client.get(
        WORKERS_URL, params={"page": 1, "page_size": 2}, headers=auth_header(admin)
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_workers_under_federation_empty_result(client, make_account, make_federation, auth_header):
    federation = make_federation()
    admin = _make_federation_admin(make_account, federation_id=federation.id)

    response = client.get(WORKERS_URL, headers=auth_header(admin))
    assert response.json()["total"] == 0


def test_workers_under_federation_missing_federation_returns_404(client, make_account, auth_header):
    admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=None)
    response = client.get(WORKERS_URL, headers=auth_header(admin))
    assert response.status_code == 404


def test_workers_under_federation_wrong_role_forbidden(
    client, make_account, make_user_profile, make_worker, make_federation, make_association, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get(WORKERS_URL, headers=auth_header(user_account)).status_code == 403

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id)
    assert client.get(WORKERS_URL, headers=auth_header(worker_account)).status_code == 403

    assoc_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    assert client.get(WORKERS_URL, headers=auth_header(assoc_admin)).status_code == 403
