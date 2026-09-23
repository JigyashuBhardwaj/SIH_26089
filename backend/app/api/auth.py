"""
Phase 5D authentication routes: `POST /auth/login`, `GET /auth/me`.

No other routes belong here — no signup, no password reset, no OTP (all
explicitly out of scope for Phase 5D). No business/domain logic either;
this router only ever touches the `Account` table.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_account
from app.auth.security import create_access_token, verify_password
from app.database import get_db
from app.models.account import Account
from app.schemas.auth import AccountPublic, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Single, generic message for every login failure mode (unknown login_id,
# wrong password, inactive account) — per the locked Phase 5D error
# design: never reveal *why* a login failed, only that it did, so a
# caller can't use the login endpoint to enumerate which login_ids exist
# or to distinguish "wrong password" from "account disabled".
_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid login credentials",
)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """
    Authenticate with `login_id` + `password` and, on success, return a
    short-lived JWT access token plus the authenticated account's public
    information. Never returns `password_hash`, never logs the submitted
    password, and never includes either in the token.
    """
    account = db.execute(
        select(Account).where(Account.login_id == payload.login_id)
    ).scalar_one_or_none()

    # `password_hash` is nullable (Phase 5C): an account with no hash set
    # yet can never successfully authenticate — treated the same as "not
    # found" rather than as a distinct error.
    if account is None or account.password_hash is None:
        raise _INVALID_CREDENTIALS

    if not verify_password(payload.password, account.password_hash):
        raise _INVALID_CREDENTIALS

    if not account.is_active:
        raise _INVALID_CREDENTIALS

    access_token = create_access_token(account_id=account.id, role=account.role)
    return LoginResponse(
        access_token=access_token,
        account=AccountPublic.model_validate(account),
    )


@router.get("/me", response_model=AccountPublic)
def read_current_account(account: Account = Depends(get_current_account)) -> AccountPublic:
    """Return the authenticated caller's own account information."""
    return AccountPublic.model_validate(account)
