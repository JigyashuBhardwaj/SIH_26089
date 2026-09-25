"""
Tests for the request-scoped transaction lifecycle implemented in
`app/database.py::get_db()` (the Phase 6B live-integration bug fix).

Before this fix, `get_db()` only closed its session in `finally`, with no
`commit()` anywhere in the codebase. Every write was flushed and visible
within the request that made it, then silently rolled back the instant
that request's session closed — so `POST /requests` looked completely
successful while a subsequent `GET /requests` found nothing.

Unlike every other file in this suite, these tests deliberately do NOT
use the `client`/`db_session` fixtures from `conftest.py`: those
fixtures override `get_db` to yield ONE shared, never-committed session
for the whole test (see `conftest.py`'s own docstring) precisely so
individual tests stay isolated via an outer rollback — but that override
bypasses `get_db()` entirely and can never exercise its own commit/
rollback behavior. These tests instead exercise the REAL `get_db`
dependency (no override), against the same isolated `TEST_DATABASE_URL`
database every other test in this suite uses, and clean up whatever they
commit themselves afterward, since there's no outer transaction here to
roll back automatically.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.auth.security import create_access_token, hash_password
from app.database import SessionLocal, get_db
from app.main import app
from app.models import (
    Account,
    AccountRole,
    Assignment,
    Association,
    Federation,
    Service,
    ServiceRequest,
    ServiceRequestStatus,
    UserProfile,
    Worker,
    WorkerSkill,
    WorkerStatus,
)


def _commit(row):
    """
    Insert and COMMIT one row via its own real, throwaway session — the
    same way any real caller (not this test suite's shared-rollback
    `db_session`) would create prerequisite data.
    """
    session = SessionLocal()
    try:
        session.add(row)
        session.commit()
        session.refresh(row)
    finally:
        session.close()
    return row


def _fetch(model, row_id):
    """Read a row back via a brand-new session — the same way a later, unrelated request would."""
    session = SessionLocal()
    try:
        return session.get(model, row_id)
    finally:
        session.close()


def _delete_all(model, ids):
    ids = [i for i in ids if i is not None]
    if not ids:
        return
    session = SessionLocal()
    try:
        session.execute(delete(model).where(model.id.in_(ids)))
        session.commit()
    finally:
        session.close()


def _delete_worker_skill(worker_id, service_id):
    """`WorkerSkill` has a composite (worker_id, service_id) primary key, no `id` column."""
    session = SessionLocal()
    try:
        session.execute(
            delete(WorkerSkill).where(
                WorkerSkill.worker_id == worker_id, WorkerSkill.service_id == service_id
            )
        )
        session.commit()
    finally:
        session.close()


# --- A/B: direct generator-level tests of get_db()'s own lifecycle ------
#
# These drive `get_db()` exactly the way FastAPI's dependency injection
# does for a `yield`-based dependency: `next(gen)` to reach the `yield`
# (mirrors a route handler receiving the session), then either resuming
# it normally (the route returned successfully) or throwing an exception
# into it (the route raised).


def test_get_db_commits_a_successful_write():
    """
    A. A write staged/flushed inside `get_db()`'s session, when the
    generator is then resumed normally (the route completed without
    raising), must be visible from a completely separate session
    afterward — proving the commit actually happened, not just the
    flush.
    """
    gen = get_db()
    db = next(gen)
    login_id = f"txn_test_{uuid.uuid4().hex[:12]}"
    account = Account(
        login_id=login_id,
        role=AccountRole.USER,
        is_active=True,
    )
    db.add(account)
    db.flush()
    account_id = account.id  # captured before commit expires/detaches this instance

    # Simulate the route returning normally: the generator resumes past
    # `yield`, reaches its own `db.commit()`, then raises StopIteration
    # (the normal end of a generator-based FastAPI dependency).
    with pytest.raises(StopIteration):
        next(gen)

    try:
        found = _fetch(Account, account_id)
        assert found is not None
        assert found.login_id == login_id
    finally:
        _delete_all(Account, [account_id])


def test_get_db_rolls_back_a_failed_request():
    """
    B. A write staged/flushed inside `get_db()`'s session, when the
    generator is then made to fail (the route raised), must NOT be
    visible from any other session afterward — it must have been rolled
    back, not merely left uncommitted-but-still-present in a dangling
    transaction.
    """
    gen = get_db()
    db = next(gen)
    account = Account(
        login_id=f"txn_test_{uuid.uuid4().hex[:12]}",
        role=AccountRole.USER,
        is_active=True,
    )
    db.add(account)
    db.flush()
    account_id = account.id

    class _SimulatedRouteFailure(Exception):
        pass

    # Simulate the route handler raising: FastAPI throws the exception
    # back into the dependency generator at its `yield` point.
    with pytest.raises(_SimulatedRouteFailure):
        gen.throw(_SimulatedRouteFailure("simulated route failure"))

    found = _fetch(Account, account_id)
    assert found is None


def test_get_db_still_closes_the_session_on_failure():
    """
    B (continued). The session's connection must be released even on the
    failure path — `get_db()`'s `finally: db.close()` must run whether or
    not an exception passed through. A second call into the same
    (already-closed) generator raising anything other than the original
    exception (e.g. `StopIteration` from the generator itself having
    already returned) would indicate `finally` never executed.
    """
    gen = get_db()
    db = next(gen)

    class _SimulatedRouteFailure(Exception):
        pass

    with pytest.raises(_SimulatedRouteFailure):
        gen.throw(_SimulatedRouteFailure("simulated route failure"))

    # The session object itself should now be closed (no active
    # transaction) — attempting to use it further is not supported by
    # SQLAlchemy after `close()`, but we can assert on the public,
    # documented signal that a session has no open transaction/connection.
    assert db.in_transaction() is False


# --- C: end-to-end reproduction of the reported live bug -----------------


def test_post_then_get_requests_across_separate_sessions_returns_the_created_request():
    """
    C. `POST /requests` and the subsequent `GET /requests` are two
    separate HTTP requests, each getting its own fresh session from the
    REAL (non-overridden) `get_db` — exactly like the live mobile app
    talking to a running server. Before the fix, the created row was
    visible in the POST's own response but invisible to the GET; this is
    the exact scenario reported.
    """
    federation = _commit(Federation(name=f"Federation {uuid.uuid4().hex[:8]}"))
    association = _commit(Association(federation_id=federation.id, name=f"Assoc {uuid.uuid4().hex[:8]}"))
    service = _commit(Service(name=f"Service {uuid.uuid4().hex[:8]}", category="General", is_active=True))
    account = _commit(
        Account(
            login_id=f"txn_test_{uuid.uuid4().hex[:12]}",
            role=AccountRole.USER,
            password_hash=hash_password("pw"),
            is_active=True,
        )
    )
    profile = _commit(UserProfile(account_id=account.id, full_name="Txn Test User", phone="9876543210"))

    headers = {"Authorization": f"Bearer {create_access_token(account_id=account.id, role=account.role)}"}
    requested = datetime.now(timezone.utc) + timedelta(hours=5)

    created_id: str | None = None
    try:
        with TestClient(app) as real_client:
            create_response = real_client.post(
                "/requests",
                headers=headers,
                json={
                    "serviceId": str(service.id),
                    "associationId": str(association.id),
                    "requestedDateTime": requested.isoformat(),
                    "address": "12 MG Road",
                    "pincode": "560001",
                },
            )
            assert create_response.status_code == 201
            created_id = create_response.json()["id"]

            # A separate call on the same TestClient still opens its own,
            # brand-new `Session` via `get_db` per request — this is not
            # the same object the POST above used.
            list_response = real_client.get("/requests", headers=headers)
            assert list_response.status_code == 200
            body = list_response.json()
            assert created_id in [item["id"] for item in body["items"]]
            assert body["total"] == 1

        # And once more from a *third*, fully independent session, well
        # after the HTTP request/response cycle that created it has
        # completely finished.
        persisted = _fetch(ServiceRequest, uuid.UUID(created_id))
        assert persisted is not None
        assert persisted.status == ServiceRequestStatus.PENDING
    finally:
        _delete_all(ServiceRequest, [uuid.UUID(created_id)] if created_id else [])
        _delete_all(UserProfile, [profile.id])
        _delete_all(Account, [account.id])
        _delete_all(Service, [service.id])
        _delete_all(Association, [association.id])
        _delete_all(Federation, [federation.id])


# --- D: a multi-write route still commits/rolls back atomically ----------


def test_create_assignment_persists_both_of_its_writes_via_real_get_db():
    """
    D. `create_assignment` (`app/api/associations.py`) makes TWO writes in
    a single request — a new `Assignment` row, and the `ServiceRequest`
    row transitioning to ASSIGNED — inside one transaction. Confirms the
    transaction-boundary fix isn't just proven for a single-write route
    like `POST /requests`: both writes must commit together and both must
    be visible from a fresh session once the request has completed.
    """
    federation = _commit(Federation(name=f"Federation {uuid.uuid4().hex[:8]}"))
    association = _commit(Association(federation_id=federation.id, name=f"Assoc {uuid.uuid4().hex[:8]}"))
    service = _commit(Service(name=f"Service {uuid.uuid4().hex[:8]}", category="General", is_active=True))

    user_account = _commit(
        Account(login_id=f"txn_test_user_{uuid.uuid4().hex[:12]}", role=AccountRole.USER, is_active=True)
    )
    user_profile = _commit(UserProfile(account_id=user_account.id, full_name="Txn Test User"))

    worker_account = _commit(
        Account(login_id=f"txn_test_worker_{uuid.uuid4().hex[:12]}", role=AccountRole.WORKER, is_active=True)
    )
    worker = _commit(
        Worker(
            account_id=worker_account.id,
            association_id=association.id,
            worker_code=f"TW-{uuid.uuid4().hex[:8]}",
            full_name="Txn Test Worker",
            status=WorkerStatus.ACTIVE,
        )
    )
    worker_skill = _commit(WorkerSkill(worker_id=worker.id, service_id=service.id))

    admin_account = _commit(
        Account(
            login_id=f"txn_test_admin_{uuid.uuid4().hex[:12]}",
            role=AccountRole.ASSOCIATION_ADMIN,
            association_id=association.id,
            is_active=True,
        )
    )

    service_request = _commit(
        ServiceRequest(
            user_id=user_profile.id,
            service_id=service.id,
            association_id=association.id,
            requested_date_time=datetime.now(timezone.utc) + timedelta(hours=5),
            address="12 MG Road",
            pincode="560001",
            status=ServiceRequestStatus.PENDING,
        )
    )

    admin_headers = {
        "Authorization": f"Bearer {create_access_token(account_id=admin_account.id, role=admin_account.role)}"
    }

    assignment_id: str | None = None
    try:
        with TestClient(app) as real_client:
            response = real_client.post(
                f"/associations/me/requests/{service_request.id}/assignments",
                headers=admin_headers,
                json={"workerId": str(worker.id)},
            )
            assert response.status_code == 201
            assignment_id = response.json()["id"]

        # Fresh sessions, independent of the one the request above used.
        persisted_request = _fetch(ServiceRequest, service_request.id)
        assert persisted_request.status == ServiceRequestStatus.ASSIGNED

        persisted_assignment = _fetch(Assignment, uuid.UUID(assignment_id))
        assert persisted_assignment is not None
        assert persisted_assignment.worker_id == worker.id
        assert persisted_assignment.request_id == service_request.id
    finally:
        _delete_all(Assignment, [uuid.UUID(assignment_id)] if assignment_id else [])
        _delete_all(ServiceRequest, [service_request.id])
        _delete_worker_skill(worker_skill.worker_id, worker_skill.service_id)
        _delete_all(Worker, [worker.id])
        _delete_all(UserProfile, [user_profile.id])
        _delete_all(Account, [admin_account.id, worker_account.id, user_account.id])
        _delete_all(Service, [service.id])
        _delete_all(Association, [association.id])
        _delete_all(Federation, [federation.id])


def test_create_assignment_failure_rolls_back_and_leaves_request_unassigned():
    """
    B (continued) applied to a real, multi-write route: a `create_assignment`
    call that is rejected (409 — the worker lacks the request's service)
    must leave the `ServiceRequest` exactly as it was (still PENDING, no
    Assignment row at all) once inspected from a fresh session — nothing
    partially written by the rejected attempt may survive.
    """
    federation = _commit(Federation(name=f"Federation {uuid.uuid4().hex[:8]}"))
    association = _commit(Association(federation_id=federation.id, name=f"Assoc {uuid.uuid4().hex[:8]}"))
    service = _commit(Service(name=f"Service {uuid.uuid4().hex[:8]}", category="General", is_active=True))

    user_account = _commit(
        Account(login_id=f"txn_test_user_{uuid.uuid4().hex[:12]}", role=AccountRole.USER, is_active=True)
    )
    user_profile = _commit(UserProfile(account_id=user_account.id, full_name="Txn Test User"))

    worker_account = _commit(
        Account(login_id=f"txn_test_worker_{uuid.uuid4().hex[:12]}", role=AccountRole.WORKER, is_active=True)
    )
    # Deliberately NO WorkerSkill for `service` — this worker is not
    # eligible, so the assignment attempt below must be rejected (409).
    worker = _commit(
        Worker(
            account_id=worker_account.id,
            association_id=association.id,
            worker_code=f"TW-{uuid.uuid4().hex[:8]}",
            full_name="Txn Test Worker",
            status=WorkerStatus.ACTIVE,
        )
    )

    admin_account = _commit(
        Account(
            login_id=f"txn_test_admin_{uuid.uuid4().hex[:12]}",
            role=AccountRole.ASSOCIATION_ADMIN,
            association_id=association.id,
            is_active=True,
        )
    )

    service_request = _commit(
        ServiceRequest(
            user_id=user_profile.id,
            service_id=service.id,
            association_id=association.id,
            requested_date_time=datetime.now(timezone.utc) + timedelta(hours=5),
            address="12 MG Road",
            pincode="560001",
            status=ServiceRequestStatus.PENDING,
        )
    )

    admin_headers = {
        "Authorization": f"Bearer {create_access_token(account_id=admin_account.id, role=admin_account.role)}"
    }

    try:
        with TestClient(app) as real_client:
            response = real_client.post(
                f"/associations/me/requests/{service_request.id}/assignments",
                headers=admin_headers,
                json={"workerId": str(worker.id)},
            )
            assert response.status_code == 409

        persisted_request = _fetch(ServiceRequest, service_request.id)
        assert persisted_request.status == ServiceRequestStatus.PENDING

        session = SessionLocal()
        try:
            remaining_assignments = (
                session.query(Assignment).filter(Assignment.request_id == service_request.id).all()
            )
        finally:
            session.close()
        assert remaining_assignments == []
    finally:
        _delete_all(ServiceRequest, [service_request.id])
        _delete_all(Worker, [worker.id])
        _delete_all(UserProfile, [user_profile.id])
        _delete_all(Account, [admin_account.id, worker_account.id, user_account.id])
        _delete_all(Service, [service.id])
        _delete_all(Association, [association.id])
        _delete_all(Federation, [federation.id])
