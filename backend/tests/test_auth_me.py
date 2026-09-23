"""
Tests for `GET /auth/me` — end-to-end, through the real `get_current_account`
dependency (as opposed to `test_auth_security.py`, which tests the JWT
encode/decode contract in isolation).
"""

TEST_PASSWORD = "correct-horse-battery-staple"


def test_valid_token_returns_200_with_own_account(client, make_account, auth_header):
    account = make_account()

    response = client.get("/auth/me", headers=auth_header(account))

    assert response.status_code == 200
    assert response.json()["id"] == str(account.id)


def test_missing_authorization_header_fails(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_malformed_token_fails(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})

    assert response.status_code == 401


def test_wrong_scheme_header_fails(client):
    response = client.get("/auth/me", headers={"Authorization": "NotBearer sometoken"})

    # Starlette/FastAPI's HTTPBearer treats a non-"Bearer" scheme as
    # equivalent to no credentials at all -- either way this must not
    # succeed.
    assert response.status_code in (401, 403)


def test_empty_bearer_token_fails(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer"})

    assert response.status_code in (401, 403)


def test_inactive_account_after_token_issuance_fails(client, make_account, auth_header, db_session):
    account = make_account()
    headers = auth_header(account)  # token issued while still active

    account.is_active = False
    db_session.flush()

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


def test_response_never_contains_password_hash(client, make_account, auth_header):
    account = make_account(password=TEST_PASSWORD)

    response = client.get("/auth/me", headers=auth_header(account))

    assert response.status_code == 200
    assert "password_hash" not in response.json()
