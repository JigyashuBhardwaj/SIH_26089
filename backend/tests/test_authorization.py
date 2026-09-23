"""
Tests for `require_role` (`app/auth/dependencies.py`).

These call the dependency's inner function directly with an already-
resolved `Account`, rather than duplicating its role-check logic — the
same approach the earlier Phase 5D manual verification used, now made
permanent and automated. End-to-end authentication (turning a Bearer
token into that `Account` in the first place) is already covered via the
real HTTP requests in `test_auth_me.py`.
"""

import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_role
from app.models.enums import AccountRole


def test_permitted_role_proceeds(make_account):
    account = make_account(role=AccountRole.FEDERATION_ADMIN)
    dependency = require_role(AccountRole.FEDERATION_ADMIN)

    result = dependency(account=account)

    assert result is account


def test_wrong_role_returns_403(make_account):
    account = make_account(role=AccountRole.USER)
    dependency = require_role(AccountRole.FEDERATION_ADMIN)

    with pytest.raises(HTTPException) as exc_info:
        dependency(account=account)

    assert exc_info.value.status_code == 403


def test_accepts_any_one_of_multiple_allowed_roles(make_account):
    account = make_account(role=AccountRole.ASSOCIATION_ADMIN)
    dependency = require_role(AccountRole.ASSOCIATION_ADMIN, AccountRole.FEDERATION_ADMIN)

    assert dependency(account=account) is account
