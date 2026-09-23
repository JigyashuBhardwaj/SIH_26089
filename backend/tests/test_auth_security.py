"""
Unit tests for `app/auth/security.py`: password hashing and the JWT
contract itself (independent of the `/auth/me` endpoint, which is tested
separately in `test_auth_me.py`).

These tests call `hash_password`/`verify_password`/`create_access_token`/
`decode_access_token` directly — no HTTP client, no database — since none
of that logic depends on either.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.models.enums import AccountRole

TEST_PASSWORD = "correct-horse-battery-staple"


# --- Password hashing -------------------------------------------------


def test_hash_password_succeeds():
    assert hash_password(TEST_PASSWORD)


def test_hash_password_is_not_plaintext():
    assert hash_password(TEST_PASSWORD) != TEST_PASSWORD


def test_verify_password_correct_returns_true():
    password_hash = hash_password(TEST_PASSWORD)
    assert verify_password(TEST_PASSWORD, password_hash) is True


def test_verify_password_incorrect_returns_false():
    password_hash = hash_password(TEST_PASSWORD)
    assert verify_password("totally-wrong-password", password_hash) is False


# --- JWT contract -------------------------------------------------------


def test_valid_token_decodes_with_expected_claims():
    account_id = uuid.uuid4()
    token = create_access_token(account_id=account_id, role=AccountRole.USER)

    payload = decode_access_token(token)

    assert payload["sub"] == str(account_id)
    assert payload["role"] == AccountRole.USER.value
    assert "iat" in payload
    assert "exp" in payload


def test_malformed_token_fails():
    with pytest.raises(TokenError):
        decode_access_token("this-is-not-a-jwt-at-all")


def test_invalid_signature_token_fails():
    account_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(account_id),
        "role": AccountRole.USER.value,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    token_signed_with_wrong_secret = jwt.encode(
        payload, "a-completely-different-secret-key", algorithm="HS256"
    )

    with pytest.raises(TokenError):
        decode_access_token(token_signed_with_wrong_secret)


def test_expired_token_fails():
    settings = get_settings()
    account_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(account_id),
        "role": AccountRole.USER.value,
        "iat": now - timedelta(minutes=60),
        "exp": now - timedelta(minutes=30),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm="HS256")

    with pytest.raises(TokenError):
        decode_access_token(expired_token)


@pytest.mark.parametrize("missing_claim", ["sub", "role", "iat", "exp"])
def test_token_missing_a_required_claim_fails(missing_claim):
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "role": AccountRole.USER.value,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    del payload[missing_claim]
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    with pytest.raises(TokenError):
        decode_access_token(token)
