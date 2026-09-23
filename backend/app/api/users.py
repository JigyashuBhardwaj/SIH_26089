"""
Phase 5E-B: `GET /users/me` — the authenticated USER's own profile.

Locked authentication/authorization flow:

    Bearer JWT -> get_current_account() -> require USER role -> Account
        -> UserProfile (looked up by Account.id, never a client-supplied id)

There is no `user_id` path/query parameter anywhere on this router: the
identity is always derived from the authenticated account, so a USER can
never request another user's profile.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.account import Account
from app.models.enums import AccountRole
from app.models.user_profile import UserProfile
from app.schemas.user import UserProfilePublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfilePublic)
def read_own_profile(
    db: Session = Depends(get_db),
    account: Account = Depends(require_role(AccountRole.USER)),
) -> UserProfilePublic:
    """
    Return the authenticated USER's own `UserProfile`. 404 if the
    authenticated account has no linked profile (there is currently no
    signup flow that guarantees one exists for every USER account).
    """
    profile = db.execute(
        select(UserProfile).where(UserProfile.account_id == account.id)
    ).scalar_one_or_none()

    if profile is None:
        raise not_found("No user profile is linked to this account")

    return UserProfilePublic.model_validate(profile)
