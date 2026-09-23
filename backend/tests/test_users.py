"""
Tests for the Phase 5E-B `GET /users/me` route.

Per the locked Phase 5E-B decision, the response does NOT include
`defaultAddress` — the locked Phase 5C `UserProfile` schema has no
address column, and adding one is out of scope for this phase.
"""

from app.models.enums import AccountRole

TEST_PASSWORD = "correct-horse-battery-staple"


def test_user_can_get_own_profile(
    client, make_account, make_user_profile, auth_header
):
    account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=account.id, full_name="Asha Verma")

    response = client.get("/users/me", headers=auth_header(account))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(profile.id)
    assert body["accountId"] == str(account.id)
    assert body["fullName"] == "Asha Verma"


def test_response_shape_has_no_default_address(
    client, make_account, make_user_profile, auth_header
):
    account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=account.id)

    response = client.get("/users/me", headers=auth_header(account))

    body = response.json()
    assert set(body.keys()) == {"id", "accountId", "fullName", "phoneNumber"}
    assert "defaultAddress" not in body


def test_returned_profile_belongs_to_authenticated_account(
    client, make_account, make_user_profile, auth_header
):
    account_a = make_account(role=AccountRole.USER)
    profile_a = make_user_profile(account_id=account_a.id, full_name="Account A")
    account_b = make_account(role=AccountRole.USER)
    make_user_profile(account_id=account_b.id, full_name="Account B")

    response = client.get("/users/me", headers=auth_header(account_a))

    body = response.json()
    assert body["id"] == str(profile_a.id)
    assert body["fullName"] == "Account A"


def test_response_never_contains_password_hash(
    client, make_account, make_user_profile, auth_header
):
    account = make_account(role=AccountRole.USER, password=TEST_PASSWORD)
    make_user_profile(account_id=account.id)

    response = client.get("/users/me", headers=auth_header(account))

    assert "password_hash" not in response.json()


def test_missing_authentication_returns_401(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_worker_role_receives_403(client, make_account, auth_header):
    account = make_account(role=AccountRole.WORKER)

    response = client.get("/users/me", headers=auth_header(account))

    assert response.status_code == 403


def test_association_admin_role_receives_403(client, make_account, auth_header):
    account = make_account(role=AccountRole.ASSOCIATION_ADMIN)

    response = client.get("/users/me", headers=auth_header(account))

    assert response.status_code == 403


def test_federation_admin_role_receives_403(client, make_account, auth_header):
    account = make_account(role=AccountRole.FEDERATION_ADMIN)

    response = client.get("/users/me", headers=auth_header(account))

    assert response.status_code == 403


def test_user_with_no_profile_receives_404(client, make_account, auth_header):
    account = make_account(role=AccountRole.USER)  # no UserProfile created

    response = client.get("/users/me", headers=auth_header(account))

    assert response.status_code == 404
