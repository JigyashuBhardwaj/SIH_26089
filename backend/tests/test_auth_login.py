"""
Tests for `POST /auth/login`.

Every failure mode (unknown login_id, wrong password, inactive account)
must be indistinguishable from the others: same status code, same body.
"""

TEST_PASSWORD = "correct-horse-battery-staple"


def test_valid_login_returns_200_with_token_and_account(client, make_account):
    account = make_account(password=TEST_PASSWORD)

    response = client.post(
        "/auth/login", json={"login_id": account.login_id, "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["account"]["id"] == str(account.id)
    assert "password_hash" not in body["account"]


def test_wrong_password_returns_401(client, make_account):
    account = make_account(password=TEST_PASSWORD)

    response = client.post(
        "/auth/login", json={"login_id": account.login_id, "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login credentials"


def test_unknown_login_id_returns_401(client):
    response = client.post(
        "/auth/login", json={"login_id": "no-such-login-id", "password": "whatever"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login credentials"


def test_inactive_account_returns_401(client, make_account):
    account = make_account(password=TEST_PASSWORD, is_active=False)

    response = client.post(
        "/auth/login", json={"login_id": account.login_id, "password": TEST_PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login credentials"


def test_account_with_no_password_set_returns_401(client, make_account):
    # password_hash is nullable on Account; an account that has never had
    # a password set must fail the same way as any other invalid login.
    account = make_account(password=None)

    response = client.post(
        "/auth/login", json={"login_id": account.login_id, "password": "anything"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login credentials"


def test_all_login_failure_modes_are_indistinguishable(client, make_account):
    """
    Wrong password, unknown login_id, and inactive account must produce
    the exact same status code and response body, so the endpoint cannot
    be used to enumerate which login_ids exist or why a login failed.
    """
    inactive_account = make_account(password=TEST_PASSWORD, is_active=False)

    wrong_password_response = client.post(
        "/auth/login", json={"login_id": inactive_account.login_id, "password": "wrong"}
    )
    unknown_login_response = client.post(
        "/auth/login", json={"login_id": "definitely-not-a-real-login-id", "password": "wrong"}
    )
    inactive_account_response = client.post(
        "/auth/login",
        json={"login_id": inactive_account.login_id, "password": TEST_PASSWORD},
    )

    assert (
        wrong_password_response.status_code
        == unknown_login_response.status_code
        == inactive_account_response.status_code
        == 401
    )
    assert (
        wrong_password_response.json()
        == unknown_login_response.json()
        == inactive_account_response.json()
    )
