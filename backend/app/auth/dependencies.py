"""
Reusable FastAPI dependencies for authentication and role authorization.

`get_current_account` is the single place that turns a raw `Authorization:
Bearer <JWT>` header into a live, verified `Account` row — every future
protected route depends on this instead of re-implementing token
verification itself. `require_role(...)` builds on top of it to add
server-side role enforcement.

Per the locked Phase 5D architecture: the JWT only identifies the
account; the database is re-checked on every request (existence,
`is_active`) so a token issued before an account was deactivated stops
working immediately, without needing any token-revocation mechanism.
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import TokenError, decode_access_token
from app.database import get_db
from app.models.account import Account
from app.models.enums import AccountRole

# auto_error=False: a missing/malformed Authorization header should reach
# our own handling below (which raises a consistent 401 with a
# WWW-Authenticate header) rather than FastAPI/Starlette's default,
# which returns 403 for a missing HTTPBearer credential.
_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Account:
    """
    Resolve the caller's `Account` from a Bearer JWT, or raise 401.

    Steps (all required, in order): a Bearer token must be present and
    well-formed; its signature and expiry must verify; its `sub` claim
    must reference an `Account` that still exists in the database; and
    that Account must still be `is_active`. Every failure raises the same
    generic 401 message, so a client can't distinguish "bad token" from
    "account no longer exists" from "account deactivated" — that
    distinction has no legitimate use on the client side and would only
    leak account state.
    """
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise _unauthorized("Could not validate credentials") from exc

    try:
        account_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise _unauthorized("Could not validate credentials") from exc

    account = db.get(Account, account_id)
    if account is None:
        raise _unauthorized("Could not validate credentials")
    if not account.is_active:
        raise _unauthorized("Could not validate credentials")

    return account


def require_role(*allowed_roles: AccountRole) -> Callable[[Account], Account]:
    """
    Build a dependency that additionally requires the authenticated
    Account's role to be one of `allowed_roles`.

    Usage: `account: Account = Depends(require_role(AccountRole.FEDERATION_ADMIN))`.
    This runs `get_current_account` first (so an unauthenticated request
    still gets 401), then checks the role server-side and rejects with
    403 if it doesn't match — the client's own notion of its role (or
    anything else it might claim) is never trusted.
    """

    def dependency(account: Account = Depends(get_current_account)) -> Account:
        if account.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return account

    return dependency
