"""
Password hashing and JWT issuance/decoding.

Password hashing uses `argon2-cffi`'s `PasswordHasher`, which defaults to
Argon2id (the variant recommended by OWASP/the PHC for password storage) —
this is the locked preference from the Phase 5D spec, and it means no
hashing algorithm is implemented by hand here; the library does the actual
cryptographic work.

JWT issuance/verification uses PyJWT with HS256, keyed by
`settings.jwt_secret_key` (see `app/config.py`). Nothing here rolls its
own cryptography: both the hashing and the signing are delegated to
well-established libraries.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.config import get_settings
from app.models.enums import AccountRole

_password_hasher = PasswordHasher()

_JWT_ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage in `Account.password_hash`."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored Argon2id hash.

    Returns False (never raises) for a wrong password OR a malformed/
    incompatible stored hash, so callers can treat every verification
    failure uniformly rather than needing to catch argon2-specific
    exceptions themselves.
    """
    try:
        _password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True


class TokenError(Exception):
    """Raised for any invalid/expired/malformed access token."""


def create_access_token(*, account_id: uuid.UUID, role: AccountRole) -> str:
    """
    Issue a short-lived signed JWT access token for `account_id`.

    Claims are deliberately minimal, per the locked Phase 5D JWT design:
    `sub` (Account UUID as a string), `role`, `iat`, `exp`. No password,
    password hash, association_id, or federation_id is ever placed in the
    token — authorization always re-derives organization scope from the
    database via the Account row itself (see `app/auth/dependencies.py`).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(account_id),
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify an access token, returning its claims.

    Raises `TokenError` for ANY problem — invalid signature, expired,
    malformed, or missing one of the required claims (`sub`, `role`,
    `iat`, `exp`) — so `get_current_account` can respond with one
    consistent "not authenticated" error regardless of the specific
    underlying JWT failure, rather than leaking which check failed.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc
