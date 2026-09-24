"""
Tests for the Phase 5E-G Worker profile/matching-data fields:
`address`, `pincode`, `rating`, `total_jobs_completed`.

Covers the model/CHECK-constraint behavior directly (inserting rows via
the ORM against the real Postgres test database, so the CHECK
constraints actually run), and confirms the three existing Worker read
APIs (`GET /workers/me`, `GET /associations/me/workers`,
`GET /federation/me/workers`) expose the four new fields in camelCase
without weakening any existing authorization/isolation rule.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import DataError, IntegrityError

from app.models.account import Account
from app.models.enums import AccountRole
from app.models.worker import (
    DEFAULT_WORKER_ADDRESS,
    DEFAULT_WORKER_PINCODE,
    DEFAULT_WORKER_RATING,
    DEFAULT_WORKER_TOTAL_JOBS_COMPLETED,
    Worker,
)


def _federation_association_account(make_federation, make_association, make_account):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    account = make_account(role=AccountRole.WORKER)
    return federation, association, account


# ===================================================== MODEL / DATABASE ===


def test_worker_can_be_created_with_valid_profile_fields(
    make_federation, make_association, make_account, make_worker, db_session
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    worker = make_worker(
        account_id=account.id,
        association_id=association.id,
        address="221B Residency Road",
        pincode="560025",
        rating=Decimal("4.50"),
        total_jobs_completed=12,
    )
    db_session.refresh(worker)
    assert worker.address == "221B Residency Road"
    assert worker.pincode == "560025"
    assert worker.rating == Decimal("4.50")
    assert worker.total_jobs_completed == 12


def test_worker_default_profile_fields_when_not_specified(
    make_federation, make_association, make_account, make_worker
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    worker = make_worker(account_id=account.id, association_id=association.id)
    assert worker.address == DEFAULT_WORKER_ADDRESS
    assert worker.pincode == DEFAULT_WORKER_PINCODE
    assert worker.rating == DEFAULT_WORKER_RATING
    assert worker.total_jobs_completed == DEFAULT_WORKER_TOTAL_JOBS_COMPLETED


@pytest.mark.parametrize("pincode", ["560001", "000000", "999999"])
def test_six_digit_pincode_is_accepted(
    make_federation, make_association, make_account, make_worker, pincode
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    worker = make_worker(account_id=account.id, association_id=association.id, pincode=pincode)
    assert worker.pincode == pincode


@pytest.mark.parametrize(
    "invalid_pincode",
    ["12345", "1234567", "56000A", "abcdef", "", "560 01"],
)
def test_invalid_pincode_is_rejected(
    make_federation, make_association, make_account, make_worker, db_session, invalid_pincode
):
    """
    Every value here must be rejected at the database level. Most trip the
    `ck_workers_pincode_six_digits` CHECK constraint (IntegrityError); a
    too-long value like "1234567" is instead rejected by the column's own
    VARCHAR(6) length limit (DataError) before the CHECK is even
    evaluated -- both are DB-level rejections of the same invalid input.
    """
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    with pytest.raises((IntegrityError, DataError)):
        make_worker(account_id=account.id, association_id=association.id, pincode=invalid_pincode)
    db_session.rollback()


@pytest.mark.parametrize("rating", [Decimal("0.00"), Decimal("5.00")])
def test_boundary_ratings_are_accepted(
    make_federation, make_association, make_account, make_worker, rating
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    worker = make_worker(account_id=account.id, association_id=association.id, rating=rating)
    assert worker.rating == rating


def test_rating_below_zero_is_rejected(
    make_federation, make_association, make_account, make_worker, db_session
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    with pytest.raises(IntegrityError):
        make_worker(account_id=account.id, association_id=association.id, rating=Decimal("-0.01"))
    db_session.rollback()


def test_rating_above_five_is_rejected(
    make_federation, make_association, make_account, make_worker, db_session
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    with pytest.raises(IntegrityError):
        make_worker(account_id=account.id, association_id=association.id, rating=Decimal("5.01"))
    db_session.rollback()


def test_total_jobs_completed_zero_is_accepted(
    make_federation, make_association, make_account, make_worker
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    worker = make_worker(
        account_id=account.id, association_id=association.id, total_jobs_completed=0
    )
    assert worker.total_jobs_completed == 0


def test_negative_total_jobs_completed_is_rejected(
    make_federation, make_association, make_account, make_worker, db_session
):
    _, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    with pytest.raises(IntegrityError):
        make_worker(
            account_id=account.id, association_id=association.id, total_jobs_completed=-1
        )
    db_session.rollback()


def test_existing_worker_relationships_continue_to_work(
    make_federation, make_association, make_account, make_worker, make_worker_skill, make_service,
    db_session,
):
    """
    Confirms adding the new columns didn't disturb Worker's existing
    relationships (account, association, skills).
    """
    federation, association, account = _federation_association_account(
        make_federation, make_association, make_account
    )
    worker = make_worker(account_id=account.id, association_id=association.id)
    service = make_service()
    make_worker_skill(worker_id=worker.id, service_id=service.id)

    db_session.refresh(worker)
    assert worker.account.id == account.id
    assert worker.association.id == association.id
    assert len(worker.skills) == 1
    assert worker.skills[0].service_id == service.id


# ============================================================ MIGRATION ===


def test_alembic_migration_upgrade_and_downgrade_round_trip():
    """
    Runs the Phase 5E-G migration's upgrade/downgrade against a
    throwaway schema built purely from Alembic (not `Base.metadata`), to
    directly validate the migration script itself -- separate from the
    ORM-model-driven `_test_schema` fixture the rest of this suite uses.
    Confirms: upgrade succeeds, the new columns/constraints exist,
    downgrade succeeds and removes exactly them, and re-upgrading is
    clean again afterward, all without touching any other table.
    """
    from pathlib import Path

    from alembic.config import Config
    from sqlalchemy import inspect

    from app.database import engine

    # Locate `backend/alembic.ini` relative to this test file using
    # `pathlib`, the same portable approach `conftest.py`'s `BACKEND_DIR`
    # already uses -- not string slicing on a literal "/tests/" separator,
    # which breaks wherever `__file__` uses a different path separator
    # (e.g. backslashes on Windows/Git Bash) and silently produces a
    # nonexistent ".../alembic.ini" path, which `Config` accepts without
    # complaint but which then has no `script_location` to read.
    backend_dir = Path(__file__).resolve().parent.parent
    backend_dir_config = Config(str(backend_dir / "alembic.ini"))

    # `alembic_version` is Alembic's own bookkeeping table, not a domain
    # table -- it doesn't exist yet on this test database (whose schema was
    # created directly from the models, not by running migrations) and is
    # created as a side effect of the `stamp` call below. Its appearance is
    # a property of exercising Alembic itself in this test, not a schema
    # change made by the Phase 5E-G migration, so it is excluded from the
    # "no other table changed" comparison alongside `workers`.
    _IGNORED_TABLES = {"workers", "alembic_version"}

    inspector_before = inspect(engine)
    other_tables_before = {
        t: sorted(c["name"] for c in inspector_before.get_columns(t))
        for t in inspector_before.get_table_names()
        if t not in _IGNORED_TABLES
    }

    from alembic import command

    # The test database's schema was created directly from the SQLAlchemy
    # models (`Base.metadata.create_all`, see conftest.py's `_test_schema`
    # fixture) rather than by actually running Alembic migrations, so it
    # has no `alembic_version` row yet. That schema already matches the
    # migration head's end state (models and the head migration are kept
    # in sync -- confirmed separately via `alembic check`), so it is safe
    # to `stamp` it to head: this only records "the DB is already at this
    # revision" without running any SQL, after which `downgrade`/`upgrade`
    # exercise this migration's real DDL against the real tables.
    command.stamp(backend_dir_config, "head")

    # Downgrade one step (removing the Phase 5E-G columns), confirming a
    # clean downgrade, then re-upgrade, confirming a clean upgrade.
    command.downgrade(backend_dir_config, "-1")

    inspector_after_downgrade = inspect(engine)
    worker_columns_after_downgrade = {
        c["name"] for c in inspector_after_downgrade.get_columns("workers")
    }
    assert "address" not in worker_columns_after_downgrade
    assert "pincode" not in worker_columns_after_downgrade
    assert "rating" not in worker_columns_after_downgrade
    assert "total_jobs_completed" not in worker_columns_after_downgrade

    command.upgrade(backend_dir_config, "+1")

    inspector_after_upgrade = inspect(engine)
    worker_columns_after_upgrade = {
        c["name"] for c in inspector_after_upgrade.get_columns("workers")
    }
    assert {"address", "pincode", "rating", "total_jobs_completed"} <= worker_columns_after_upgrade

    check_constraint_names = {
        c["name"] for c in inspector_after_upgrade.get_check_constraints("workers")
    }
    assert "ck_workers_pincode_six_digits" in check_constraint_names
    assert "ck_workers_rating_range" in check_constraint_names
    assert "ck_workers_total_jobs_completed_non_negative" in check_constraint_names

    # No other table's columns changed.
    other_tables_after = {
        t: sorted(c["name"] for c in inspector_after_upgrade.get_columns(t))
        for t in inspector_after_upgrade.get_table_names()
        if t not in _IGNORED_TABLES
    }
    assert other_tables_after == other_tables_before


# =================================================================== API ==


def test_get_workers_me_exposes_new_fields(client, make_federation, make_association, make_account, make_worker, auth_header):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    account = make_account(role=AccountRole.WORKER)
    worker = make_worker(
        account_id=account.id,
        association_id=association.id,
        address="12 Church Street",
        pincode="560001",
        rating=Decimal("4.25"),
        total_jobs_completed=7,
    )

    response = client.get("/workers/me", headers=auth_header(account))
    assert response.status_code == 200
    body = response.json()
    assert body["address"] == "12 Church Street"
    assert body["pincode"] == "560001"
    assert body["rating"] == "4.25"
    assert body["totalJobsCompleted"] == 7
    assert "password_hash" not in response.text
    assert "passwordHash" not in response.text


def test_get_associations_me_workers_exposes_new_fields(
    client, make_federation, make_association, make_account, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(
        account_id=worker_account.id,
        association_id=association.id,
        address="45 Brigade Road",
        pincode="560025",
        rating=Decimal("3.80"),
        total_jobs_completed=3,
    )

    response = client.get("/associations/me/workers", headers=auth_header(admin))
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["address"] == "45 Brigade Road"
    assert item["pincode"] == "560025"
    assert item["rating"] == "3.80"
    assert item["totalJobsCompleted"] == 3


def test_get_federation_me_workers_exposes_new_fields(
    client, make_federation, make_association, make_account, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(
        account_id=worker_account.id,
        association_id=association.id,
        address="9 Residency Road",
        pincode="560025",
        rating=Decimal("5.00"),
        total_jobs_completed=99,
    )

    response = client.get("/federation/me/workers", headers=auth_header(fed_admin))
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["address"] == "9 Residency Road"
    assert item["pincode"] == "560025"
    assert item["rating"] == "5.00"
    assert item["totalJobsCompleted"] == 99


def test_worker_apis_authorization_rules_still_intact(
    client, make_federation, make_association, make_account, make_worker, make_user_profile, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)

    assert client.get("/workers/me").status_code == 401
    assert client.get("/associations/me/workers").status_code == 401
    assert client.get("/federation/me/workers").status_code == 401

    user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=user_account.id)
    assert client.get("/workers/me", headers=auth_header(user_account)).status_code == 403
    assert client.get("/associations/me/workers", headers=auth_header(user_account)).status_code == 403
    assert client.get("/federation/me/workers", headers=auth_header(user_account)).status_code == 403


def test_association_isolation_still_intact(
    client, make_federation, make_association, make_account, make_worker, auth_header
):
    federation = make_federation()
    association_a = make_association(federation_id=federation.id)
    association_b = make_association(federation_id=federation.id)
    admin_a = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association_a.id)

    worker_account_b = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account_b.id, association_id=association_b.id)

    response = client.get("/associations/me/workers", headers=auth_header(admin_a))
    assert response.json()["total"] == 0


def test_federation_scope_still_intact(
    client, make_federation, make_association, make_account, make_worker, auth_header
):
    federation_a = make_federation()
    federation_b = make_federation()
    association_b = make_association(federation_id=federation_b.id)
    fed_admin_a = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation_a.id)

    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association_b.id)

    response = client.get("/federation/me/workers", headers=auth_header(fed_admin_a))
    assert response.json()["total"] == 0


def test_worker_response_uses_camel_case(
    client, make_federation, make_association, make_account, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=account.id, association_id=association.id)

    response = client.get("/workers/me", headers=auth_header(account))
    body = response.json()
    assert "total_jobs_completed" not in body
    assert "totalJobsCompleted" in body
    assert "account_id" not in body
    assert "accountId" in body


def test_no_sensitive_account_data_exposed(
    client, make_federation, make_association, make_account, make_worker, auth_header
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    account = make_account(role=AccountRole.WORKER, password="secret123")
    make_worker(account_id=account.id, association_id=association.id)

    response = client.get("/workers/me", headers=auth_header(account))
    assert "password" not in response.text.lower()
