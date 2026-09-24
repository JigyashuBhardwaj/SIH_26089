"""
Phase 5F — tests for `backend/scripts/seed_demo_data.py`.

These tests exercise `seed_demo_data.run_seed()` directly against the
existing `db_session` fixture's isolated, rollback-only test-database
connection (see `tests/conftest.py`) -- `run_seed()` is a plain function
that takes an injected `Session` and never opens its own connection or
calls `commit()`/`rollback()` itself, which is exactly what makes this
possible without ever touching a real database safety guard, and without
weakening that guard (`main()`'s CLI/safety-check path is entirely
separate and is exercised only by the safety-guard tests below, which
never open a session).
"""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

import scripts.seed_demo_data as seed_demo_data
from app.database import engine
from app.models import (
    Account,
    AccountRole,
    Association,
    Federation,
    Service,
    UserProfile,
    Worker,
    WorkerSkill,
)


# ==========================================================================
# Pure generator tests -- no database involved
# ==========================================================================


def test_generated_worker_counts_match_admin_dataset():
    workers = seed_demo_data.generate_demo_workers()
    assert len(workers) == 215
    assert sum(1 for w in workers if w.association_slug == "dhanbad_skilled") == 120
    assert sum(1 for w in workers if w.association_slug == "dhanbad_general") == 95


def test_generated_worker_codes_are_unique():
    workers = seed_demo_data.generate_demo_workers()
    codes = {w.worker_code for w in workers}
    assert len(codes) == len(workers)


def test_deterministic_worker_generation_is_reproducible():
    """Calling the generator twice must produce byte-identical output --
    this is the whole premise of reproducing admin/src/data/workerCatalog.ts
    without a fixed database to check against."""
    first = seed_demo_data.generate_demo_workers()
    second = seed_demo_data.generate_demo_workers()
    assert first == second


def test_mukesh_yadav_generated_identity_and_override():
    workers = seed_demo_data.generate_demo_workers()
    mukesh = next(w for w in workers if w.worker_code == "SKW-0066")
    assert mukesh.full_name == "Mukesh Yadav"
    assert mukesh.association_slug == "dhanbad_skilled"
    assert mukesh.address == "House no. 108, Sector 4, Dhanbad, Jharkhand"
    assert mukesh.pincode == "826004"
    assert mukesh.rating == 4.8
    assert mukesh.total_jobs_completed == 42

    # A second, independently-generated "Mukesh Yadav" must exist and must
    # NOT have received the override (worker_code is authoritative, not name).
    other_mukesh = next(w for w in workers if w.worker_code == "SKW-0080")
    assert other_mukesh.full_name == "Mukesh Yadav"
    assert other_mukesh.total_jobs_completed != 42 or other_mukesh.address != mukesh.address


def test_service_mapping_covers_every_generated_skill():
    workers = seed_demo_data.generate_demo_workers()
    for worker in workers:
        for skill in worker.skills:
            assert skill in seed_demo_data._SKILL_TO_SERVICE_NAME
            assert seed_demo_data._SKILL_TO_SERVICE_NAME[skill] in seed_demo_data.SERVICE_CATALOGUE


def test_every_worker_has_at_least_one_mappable_skill():
    workers = seed_demo_data.generate_demo_workers()
    for worker in workers:
        assert len(worker.skills) >= 1


# ==========================================================================
# Database safety guard tests -- no session ever opened
# ==========================================================================


def test_safety_guard_rejects_a_test_database():
    with pytest.raises(seed_demo_data.SeedSafetyError, match="test"):
        seed_demo_data._check_database_safety(
            "postgresql://user:pw@localhost:5432/karmanya_test", allow_dev=True
        )


def test_safety_guard_requires_explicit_flag_for_non_test_database():
    with pytest.raises(seed_demo_data.SeedSafetyError, match="yes-seed-development"):
        seed_demo_data._check_database_safety(
            "postgresql://user:pw@localhost:5432/karmanya", allow_dev=False
        )


def test_safety_guard_allows_non_test_database_with_explicit_flag():
    db_name = seed_demo_data._check_database_safety(
        "postgresql://user:pw@localhost:5432/karmanya", allow_dev=True
    )
    assert db_name == "karmanya"


# ==========================================================================
# Database-backed tests, via db_session (rollback-only, isolated per test)
# ==========================================================================


def test_fresh_seed_creates_expected_dataset(db_session):
    result = seed_demo_data.run_seed(db_session)

    assert result.worker_count == 215
    assert result.service_count == 9
    assert db_session.execute(select(func.count()).select_from(Federation)).scalar_one() == 1
    assert db_session.execute(select(func.count()).select_from(Association)).scalar_one() == 2
    assert db_session.execute(select(func.count()).select_from(Service)).scalar_one() == 9
    assert db_session.execute(select(func.count()).select_from(Worker)).scalar_one() == 215
    worker_account_count = db_session.execute(
        select(func.count()).select_from(Account).where(Account.role == AccountRole.WORKER)
    ).scalar_one()
    assert worker_account_count == 215


def test_second_seed_is_idempotent(db_session):
    seed_demo_data.run_seed(db_session)
    result_second = seed_demo_data.run_seed(db_session)

    assert result_second.worker_count == 215
    assert db_session.execute(select(func.count()).select_from(Worker)).scalar_one() == 215
    assert db_session.execute(select(func.count()).select_from(Association)).scalar_one() == 2
    assert db_session.execute(select(func.count()).select_from(Federation)).scalar_one() == 1


def test_counts_and_identities_unchanged_after_second_seed(db_session):
    seed_demo_data.run_seed(db_session)
    worker_ids_before = set(db_session.execute(select(Worker.id)).scalars().all())
    account_ids_before = set(db_session.execute(select(Account.id)).scalars().all())

    seed_demo_data.run_seed(db_session)

    worker_ids_after = set(db_session.execute(select(Worker.id)).scalars().all())
    account_ids_after = set(db_session.execute(select(Account.id)).scalars().all())
    assert worker_ids_before == worker_ids_after
    assert account_ids_before == account_ids_after


def test_no_duplicate_services_after_rerun(db_session):
    seed_demo_data.run_seed(db_session)
    seed_demo_data.run_seed(db_session)

    names = db_session.execute(select(Service.name)).scalars().all()
    assert len(names) == len(set(names)) == 9


def test_no_duplicate_accounts_after_rerun(db_session):
    seed_demo_data.run_seed(db_session)
    seed_demo_data.run_seed(db_session)

    login_ids = db_session.execute(select(Account.login_id)).scalars().all()
    assert len(login_ids) == len(set(login_ids))
    # 4 org-level accounts + 215 worker accounts.
    assert len(login_ids) == 219


def test_no_duplicate_workers_after_rerun(db_session):
    seed_demo_data.run_seed(db_session)
    seed_demo_data.run_seed(db_session)

    worker_codes = db_session.execute(select(Worker.worker_code)).scalars().all()
    assert len(worker_codes) == len(set(worker_codes)) == 215


def test_no_duplicate_worker_skill_after_rerun(db_session):
    seed_demo_data.run_seed(db_session)
    seed_demo_data.run_seed(db_session)

    pairs = db_session.execute(select(WorkerSkill.worker_id, WorkerSkill.service_id)).all()
    assert len(pairs) == len(set(pairs))


def test_mukesh_override_persisted_exactly(db_session):
    seed_demo_data.run_seed(db_session)

    mukesh = db_session.execute(
        select(Worker).where(Worker.worker_code == "SKW-0066")
    ).scalar_one()
    assert mukesh.full_name == "Mukesh Yadav"
    assert mukesh.address == "House no. 108, Sector 4, Dhanbad, Jharkhand"
    assert mukesh.pincode == "826004"
    assert float(mukesh.rating) == 4.80
    assert mukesh.total_jobs_completed == 42
    assert mukesh.association_id == seed_demo_data.ASSOCIATION_SKILLED_ID

    generated = next(
        w for w in seed_demo_data.generate_demo_workers() if w.worker_code == "SKW-0066"
    )
    assert mukesh.phone == generated.phone_number

    # SKW-0080 (the other generated "Mukesh Yadav") must NOT carry the override.
    other = db_session.execute(select(Worker).where(Worker.worker_code == "SKW-0080")).scalar_one()
    assert not (
        other.address == mukesh.address
        and other.total_jobs_completed == mukesh.total_jobs_completed
    )


def test_mukesh_override_restored_after_drift_and_rerun(db_session):
    seed_demo_data.run_seed(db_session)

    mukesh = db_session.execute(select(Worker).where(Worker.worker_code == "SKW-0066")).scalar_one()
    mukesh.address = "Some other address that drifted"
    mukesh.total_jobs_completed = 999
    db_session.flush()

    seed_demo_data.run_seed(db_session)

    mukesh = db_session.execute(select(Worker).where(Worker.worker_code == "SKW-0066")).scalar_one()
    assert mukesh.address == "House no. 108, Sector 4, Dhanbad, Jharkhand"
    assert mukesh.total_jobs_completed == 42


def test_every_worker_has_full_name_and_matching_phone(db_session):
    seed_demo_data.run_seed(db_session)

    generated_by_code = {w.worker_code: w for w in seed_demo_data.generate_demo_workers()}
    workers = db_session.execute(select(Worker)).scalars().all()
    assert len(workers) == 215
    for worker in workers:
        assert worker.full_name  # NOT NULL column -- must never be empty/None
        generated = generated_by_code[worker.worker_code]
        assert worker.full_name == generated.full_name
        assert worker.phone == generated.phone_number


def test_correct_association_membership(db_session):
    seed_demo_data.run_seed(db_session)

    skilled_count = db_session.execute(
        select(func.count()).select_from(Worker).where(
            Worker.association_id == seed_demo_data.ASSOCIATION_SKILLED_ID
        )
    ).scalar_one()
    general_count = db_session.execute(
        select(func.count()).select_from(Worker).where(
            Worker.association_id == seed_demo_data.ASSOCIATION_GENERAL_ID
        )
    ).scalar_one()
    assert skilled_count == 120
    assert general_count == 95


def test_all_workers_have_at_least_one_skill(db_session):
    seed_demo_data.run_seed(db_session)

    worker_ids = set(db_session.execute(select(Worker.id)).scalars().all())
    workers_with_skill = set(db_session.execute(select(WorkerSkill.worker_id)).scalars().all())
    assert worker_ids <= workers_with_skill


def test_every_service_has_at_least_one_worker(db_session):
    seed_demo_data.run_seed(db_session)

    service_ids = set(db_session.execute(select(Service.id)).scalars().all())
    services_with_worker = set(db_session.execute(select(WorkerSkill.service_id)).scalars().all())
    assert service_ids <= services_with_worker


def test_worker_account_role_and_association_consistency(db_session):
    seed_demo_data.run_seed(db_session)

    workers = db_session.execute(select(Worker)).scalars().all()
    accounts_by_id = {a.id: a for a in db_session.execute(select(Account)).scalars().all()}
    assert len(workers) == 215
    for worker in workers:
        account = accounts_by_id[worker.account_id]
        assert account.role == AccountRole.WORKER
        assert account.association_id == worker.association_id
        assert account.federation_id is None


def test_demo_user_and_profile_created(db_session):
    seed_demo_data.run_seed(db_session)

    demo_user = db_session.execute(
        select(Account).where(Account.login_id == "demo_user")
    ).scalar_one()
    assert demo_user.role == AccountRole.USER

    profile = db_session.execute(
        select(UserProfile).where(UserProfile.account_id == demo_user.id)
    ).scalar_one()
    assert profile.full_name == "Madhav"


def test_password_hash_verification(db_session):
    from app.auth.security import verify_password

    seed_demo_data.run_seed(db_session)

    federation_admin = db_session.execute(
        select(Account).where(Account.login_id == "federation_admin")
    ).scalar_one()
    assert verify_password("federation123", federation_admin.password_hash)

    dhanbad_skilled = db_session.execute(
        select(Account).where(Account.login_id == "dhanbad_skilled")
    ).scalar_one()
    assert verify_password("skilled123", dhanbad_skilled.password_hash)

    dhanbad_general = db_session.execute(
        select(Account).where(Account.login_id == "dhanbad_general")
    ).scalar_one()
    assert verify_password("general123", dhanbad_general.password_hash)

    demo_user = db_session.execute(
        select(Account).where(Account.login_id == "demo_user")
    ).scalar_one()
    assert verify_password("user123", demo_user.password_hash)

    mukesh_account = db_session.execute(
        select(Account).where(Account.login_id == "SKW-0066")
    ).scalar_one()
    assert verify_password("skw0066123", mukesh_account.password_hash)
    assert not verify_password("wrong-password", mukesh_account.password_hash)


def test_password_hash_unchanged_on_normal_rerun(db_session):
    """A rerun where nothing drifted must leave the stored Argon2id hash
    string byte-for-byte unchanged -- not just still verifiable, but
    literally not rewritten (proves the reconcile path checks before
    replacing rather than unconditionally rehashing)."""
    seed_demo_data.run_seed(db_session)

    dhanbad_skilled_before = db_session.execute(
        select(Account).where(Account.login_id == "dhanbad_skilled")
    ).scalar_one()
    mukesh_account_before = db_session.execute(
        select(Account).where(Account.login_id == "SKW-0066")
    ).scalar_one()
    hash_before_org = dhanbad_skilled_before.password_hash
    hash_before_worker = mukesh_account_before.password_hash

    seed_demo_data.run_seed(db_session)

    dhanbad_skilled_after = db_session.execute(
        select(Account).where(Account.login_id == "dhanbad_skilled")
    ).scalar_one()
    mukesh_account_after = db_session.execute(
        select(Account).where(Account.login_id == "SKW-0066")
    ).scalar_one()
    assert dhanbad_skilled_after.password_hash == hash_before_org
    assert mukesh_account_after.password_hash == hash_before_worker


def test_password_drift_is_restored_on_rerun(db_session):
    """An account whose password_hash was deliberately replaced with a
    DIFFERENT valid Argon2id hash must have the canonical demo password
    restored on the next seed run."""
    from app.auth.security import hash_password, verify_password

    seed_demo_data.run_seed(db_session)

    dhanbad_skilled = db_session.execute(
        select(Account).where(Account.login_id == "dhanbad_skilled")
    ).scalar_one()
    drifted_hash = hash_password("some-completely-different-password")
    dhanbad_skilled.password_hash = drifted_hash
    db_session.flush()
    assert not verify_password("skilled123", dhanbad_skilled.password_hash)

    mukesh_account = db_session.execute(
        select(Account).where(Account.login_id == "SKW-0066")
    ).scalar_one()
    mukesh_account.password_hash = hash_password("another-different-password")
    db_session.flush()
    assert not verify_password("skw0066123", mukesh_account.password_hash)

    seed_demo_data.run_seed(db_session)

    dhanbad_skilled = db_session.execute(
        select(Account).where(Account.login_id == "dhanbad_skilled")
    ).scalar_one()
    assert verify_password("skilled123", dhanbad_skilled.password_hash)
    assert dhanbad_skilled.password_hash != drifted_hash

    mukesh_account = db_session.execute(
        select(Account).where(Account.login_id == "SKW-0066")
    ).scalar_one()
    assert verify_password("skw0066123", mukesh_account.password_hash)


def test_unrelated_rows_survive_a_rerun_untouched(db_session):
    """Ownership-based validation: after a successful canonical seed, an
    unrelated Worker/Account/Service is inserted; the seed is run again;
    it must succeed and must leave the unrelated rows completely
    untouched."""
    seed_demo_data.run_seed(db_session)

    skilled_association_id = seed_demo_data.ASSOCIATION_SKILLED_ID

    unrelated_service = Service(name="Unrelated Demo Service", category="Something Else", is_active=True)
    db_session.add(unrelated_service)
    db_session.flush()

    unrelated_account = Account(
        id=uuid.uuid4(),
        login_id="UNRELATED-0001",
        role=AccountRole.WORKER,
        password_hash="not-a-real-hash",
        association_id=skilled_association_id,
        federation_id=None,
        is_active=True,
    )
    db_session.add(unrelated_account)
    db_session.flush()

    unrelated_worker = Worker(
        id=uuid.uuid4(),
        account_id=unrelated_account.id,
        association_id=skilled_association_id,
        worker_code="UNRELATED-0001",
        full_name="Not A Demo Worker",
        phone="+91-99999-99999",
        address="Somewhere else entirely",
        pincode="826099",
        rating="3.33",
        total_jobs_completed=7,
        status=seed_demo_data.WorkerStatus.ACTIVE,
    )
    db_session.add(unrelated_worker)
    db_session.flush()
    unrelated_skill = WorkerSkill(worker_id=unrelated_worker.id, service_id=unrelated_service.id)
    db_session.add(unrelated_skill)
    db_session.flush()

    # The unrelated Worker's login_id/worker_code is deliberately made to
    # look nothing like a canonical "SKW-####"/"GEN-####" code, so it can
    # never collide with the canonical dataset's own identity keys.
    result = seed_demo_data.run_seed(db_session)
    assert result.worker_count == 215

    still_there_service = db_session.execute(
        select(Service).where(Service.name == "Unrelated Demo Service")
    ).scalar_one()
    assert still_there_service.category == "Something Else"
    assert still_there_service.is_active is True

    still_there_account = db_session.execute(
        select(Account).where(Account.login_id == "UNRELATED-0001")
    ).scalar_one()
    assert still_there_account.password_hash == "not-a-real-hash"
    assert still_there_account.association_id == skilled_association_id

    still_there_worker = db_session.execute(
        select(Worker).where(Worker.worker_code == "UNRELATED-0001")
    ).scalar_one()
    assert still_there_worker.full_name == "Not A Demo Worker"
    assert still_there_worker.address == "Somewhere else entirely"
    assert still_there_worker.total_jobs_completed == 7

    still_there_skill = db_session.execute(
        select(WorkerSkill).where(
            WorkerSkill.worker_id == unrelated_worker.id, WorkerSkill.service_id == unrelated_service.id
        )
    ).scalar_one_or_none()
    assert still_there_skill is not None


def test_association_uses_fixed_uuid_and_conflict_is_rejected(db_session):
    """A row already occupying the fixed Association UUID with an
    unexpected name must cause a loud failure, never a silent overwrite."""
    conflicting = Association(
        id=seed_demo_data.ASSOCIATION_SKILLED_ID,
        name="Some Unrelated Association",
        federation_id=uuid.uuid4(),
    )
    # federation_id FK must reference a real row for the insert itself
    # to succeed, so create a throwaway federation for it.
    unrelated_federation = Federation(id=conflicting.federation_id, name="Unrelated Federation")
    db_session.add(unrelated_federation)
    db_session.add(conflicting)
    db_session.flush()

    with pytest.raises(seed_demo_data.SeedIntegrityError):
        seed_demo_data.run_seed(db_session)


def test_rollback_on_deliberate_failure(monkeypatch):
    """`run_seed` never commits or rolls back itself -- verify that a
    caller-driven rollback after a forced validation failure leaves
    nothing behind, using a dedicated connection/transaction exactly like
    `tests/conftest.py`'s own `db_session` fixture does."""
    connection = engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()

    def _always_fail(*args, **kwargs):
        raise seed_demo_data.SeedValidationError("forced failure for testing rollback")

    monkeypatch.setattr(seed_demo_data, "validate_seed", _always_fail)

    try:
        with pytest.raises(seed_demo_data.SeedValidationError):
            seed_demo_data.run_seed(session)
        session.rollback()

        federation_count = session.execute(select(func.count()).select_from(Federation)).scalar_one()
        worker_count = session.execute(select(func.count()).select_from(Worker)).scalar_one()
        assert federation_count == 0
        assert worker_count == 0
    finally:
        # `session.rollback()` above already ends the transaction this
        # connection's session was bound to -- calling `transaction.rollback()`
        # again here would just be a harmless-but-noisy no-op, so only close
        # what's left open.
        session.close()
        connection.close()
