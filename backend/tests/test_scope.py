"""
Tests for the organization-scope foundations in `app/auth/scope.py`.

None of these are wired into any route yet (per the locked Phase 5D/5E-A
scope), so they're exercised directly with database-backed fixtures
rather than through HTTP.
"""

import pytest
from fastapi import HTTPException

from app.auth.scope import (
    ensure_association_admin_scope,
    ensure_federation_admin_scope,
    get_federation_association_ids,
    get_worker_association_id,
)
from app.models.enums import AccountRole


# --- Association Admin ---------------------------------------------------


def test_association_admin_can_access_own_association(make_federation, make_association, make_account):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    ensure_association_admin_scope(admin, association.id)  # must not raise


def test_association_admin_cannot_access_another_association(
    make_federation, make_association, make_account
):
    federation = make_federation()
    own_association = make_association(federation_id=federation.id)
    other_association = make_association(federation_id=federation.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=own_association.id)

    with pytest.raises(HTTPException) as exc_info:
        ensure_association_admin_scope(admin, other_association.id)

    assert exc_info.value.status_code == 403


# --- Federation Admin ------------------------------------------------------


def test_federation_admin_can_access_association_in_own_federation(
    db_session, make_federation, make_association, make_account
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    federation_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)

    ensure_federation_admin_scope(db_session, federation_admin, association.id)  # must not raise


def test_federation_admin_cannot_access_association_outside_own_federation(
    db_session, make_federation, make_association, make_account
):
    own_federation = make_federation()
    other_federation = make_federation()
    other_association = make_association(federation_id=other_federation.id)
    federation_admin = make_account(
        role=AccountRole.FEDERATION_ADMIN, federation_id=own_federation.id
    )

    with pytest.raises(HTTPException) as exc_info:
        ensure_federation_admin_scope(db_session, federation_admin, other_association.id)

    assert exc_info.value.status_code == 403


def test_get_federation_association_ids_returns_only_own_federation(
    db_session, make_federation, make_association, make_account
):
    own_federation = make_federation()
    other_federation = make_federation()
    own_association_a = make_association(federation_id=own_federation.id)
    own_association_b = make_association(federation_id=own_federation.id)
    make_association(federation_id=other_federation.id)  # belongs to a different federation
    federation_admin = make_account(
        role=AccountRole.FEDERATION_ADMIN, federation_id=own_federation.id
    )

    ids = get_federation_association_ids(db_session, federation_admin)

    assert set(ids) == {own_association_a.id, own_association_b.id}


# --- Worker ------------------------------------------------------------


def test_worker_association_scope_is_derived_from_db_relationship(
    db_session, make_federation, make_association, make_account, make_worker
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id)

    derived_association_id = get_worker_association_id(db_session, worker_account)

    assert derived_association_id == association.id


def test_worker_scope_404s_when_no_worker_profile_is_linked(db_session, make_account):
    worker_account = make_account(role=AccountRole.WORKER)

    with pytest.raises(HTTPException) as exc_info:
        get_worker_association_id(db_session, worker_account)

    assert exc_info.value.status_code == 404
