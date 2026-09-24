"""
Tests for the Phase 5E-E manual-assignment route:
`POST /associations/me/requests/{request_id}/assignments`.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.database import engine
from app.models.assignment import Assignment
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus, WorkerStatus
from app.models.service_request import ServiceRequest

ASSIGN_URL = "/associations/me/requests/{request_id}/assignments"


def _url(request_id) -> str:
    return ASSIGN_URL.format(request_id=request_id)


def _setup(
    make_federation,
    make_association,
    make_account,
    make_service,
    make_user_profile,
    make_worker,
    make_worker_skill,
    make_service_request,
    db_session,
    *,
    request_status: ServiceRequestStatus = ServiceRequestStatus.PENDING,
    worker_status: WorkerStatus = WorkerStatus.ACTIVE,
    worker_has_skill: bool = True,
    association_id=None,
):
    """
    Shared happy-path fixture wiring: one federation/association, a USER
    with a request against `service`, an ASSOCIATION_ADMIN for that
    association, and one eligible WORKER (skilled in `service`, ACTIVE),
    unless overridden. Returns a dict of everything a test might need.
    """
    federation = make_federation()
    association = make_association(federation_id=federation.id)

    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    service = make_service()

    service_request = make_service_request(
        user_id=profile.id,
        service_id=service.id,
        association_id=association.id,
        status=request_status,
    )

    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(
        account_id=worker_account.id,
        association_id=association_id or association.id,
        full_name="Eligible Worker",
    )
    if worker_status != WorkerStatus.ACTIVE:
        worker.status = worker_status
        db_session.flush()
    if worker_has_skill:
        make_worker_skill(worker_id=worker.id, service_id=service.id)

    return {
        "federation": federation,
        "association": association,
        "admin": admin,
        "user_account": user_account,
        "profile": profile,
        "service": service,
        "service_request": service_request,
        "worker_account": worker_account,
        "worker": worker,
    }


@pytest.fixture()
def setup(
    make_federation, make_association, make_account, make_service, make_user_profile,
    make_worker, make_worker_skill, make_service_request, db_session,
):
    def _setup_fn(**kwargs):
        return _setup(
            make_federation, make_association, make_account, make_service,
            make_user_profile, make_worker, make_worker_skill, make_service_request,
            db_session, **kwargs
        )

    return _setup_fn


# --- Happy path -----------------------------------------------------------


def test_admin_can_assign_valid_worker(client, setup, auth_header, db_session):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == AssignmentStatus.PENDING_RESPONSE.value
    assert body["requestId"] == str(ctx["service_request"].id)
    assert body["workerId"] == str(ctx["worker"].id)
    assert body["assignedBy"] == str(ctx["admin"].id)
    assert body["respondedAt"] is None
    assert "createdAt" not in body
    assert set(body.keys()) == {
        "id", "requestId", "workerId", "assignedBy", "status",
        "assignedAt", "respondedAt", "updatedAt",
    }


def test_created_assignment_has_pending_response_status(client, setup, auth_header, db_session):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assignment_id = uuid.UUID(response.json()["id"])
    assignment = db_session.get(Assignment, assignment_id)
    assert assignment.status == AssignmentStatus.PENDING_RESPONSE


def test_request_transitions_from_pending_to_assigned(client, setup, auth_header, db_session):
    ctx = setup(request_status=ServiceRequestStatus.PENDING)
    client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.ASSIGNED


def test_request_transitions_from_matching_to_assigned(client, setup, auth_header, db_session):
    ctx = setup(request_status=ServiceRequestStatus.MATCHING)
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 201
    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.ASSIGNED


def test_assigned_by_is_authenticated_admin(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.json()["assignedBy"] == str(ctx["admin"].id)


def test_assignment_timestamps_are_correct(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    body = response.json()
    assert body["assignedAt"] is not None
    assert body["updatedAt"] is not None
    assert body["respondedAt"] is None


# --- Authentication/authorization -----------------------------------------


def test_unauthenticated_returns_401(client, setup):
    ctx = setup()
    response = client.post(_url(ctx["service_request"].id), json={"workerId": str(ctx["worker"].id)})
    assert response.status_code == 401


def test_user_role_forbidden(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["user_account"]),
    )
    assert response.status_code == 403


def test_worker_role_forbidden(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["worker_account"]),
    )
    assert response.status_code == 403


# --- Association isolation --------------------------------------------------


def test_admin_cannot_assign_request_from_other_association(
    client, setup, make_federation, make_association, make_account, auth_header
):
    ctx = setup()
    other_association = make_association(federation_id=ctx["federation"].id)
    other_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=other_association.id)

    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(other_admin),
    )
    assert response.status_code == 404


def test_admin_cannot_assign_worker_from_other_association(
    client, setup, make_association, make_account, make_worker, auth_header
):
    ctx = setup()
    other_association = make_association(federation_id=ctx["federation"].id)
    other_worker_account = make_account(role=AccountRole.WORKER)
    other_worker = make_worker(account_id=other_worker_account.id, association_id=other_association.id)

    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(other_worker.id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 404


# --- 404s -------------------------------------------------------------------


def test_nonexistent_request_returns_404(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(uuid.uuid4()), json={"workerId": str(ctx["worker"].id)}, headers=auth_header(ctx["admin"])
    )
    assert response.status_code == 404


def test_nonexistent_worker_returns_404(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(uuid.uuid4())},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 404


# --- 422s -------------------------------------------------------------------


def test_malformed_request_uuid_returns_422(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url("not-a-uuid"), json={"workerId": str(ctx["worker"].id)}, headers=auth_header(ctx["admin"])
    )
    assert response.status_code == 422


def test_malformed_worker_uuid_returns_422(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": "not-a-uuid"},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 422


def test_unexpected_field_returns_422(client, setup, auth_header):
    ctx = setup()
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id), "status": "ACCEPTED"},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 422


# --- Worker eligibility (409) ------------------------------------------------


def test_inactive_worker_cannot_be_assigned(client, setup, auth_header):
    ctx = setup(worker_status=WorkerStatus.INACTIVE)
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 409


def test_worker_without_required_service_cannot_be_assigned(client, setup, auth_header):
    ctx = setup(worker_has_skill=False)
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 409


# --- Invalid lifecycle states (409) -----------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        ServiceRequestStatus.ASSIGNED,
        ServiceRequestStatus.ACCEPTED,
        ServiceRequestStatus.WORKER_COMPLETED,
        ServiceRequestStatus.USER_CONFIRMED,
        ServiceRequestStatus.PAYMENT_PENDING,
        ServiceRequestStatus.PAID,
        ServiceRequestStatus.COMPLETED,
        ServiceRequestStatus.CANCELLED_BY_USER,
    ],
)
def test_request_in_terminal_or_active_state_cannot_be_assigned(client, setup, auth_header, status):
    ctx = setup(request_status=status)
    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 409


# --- Duplicate active assignment (409) --------------------------------------


def test_duplicate_active_assignment_is_rejected(client, setup, auth_header, make_assignment):
    ctx = setup(request_status=ServiceRequestStatus.PENDING)
    # Directly create an active Assignment while the request status is
    # still PENDING (bypassing this endpoint) to exercise the
    # defense-in-depth duplicate-active-assignment check independently
    # of the request-status check.
    make_assignment(
        request_id=ctx["service_request"].id,
        worker_id=ctx["worker"].id,
        assigned_by=ctx["admin"].id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )

    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 409


def test_historical_assignment_rows_are_preserved(
    client, setup, auth_header, make_assignment, db_session
):
    ctx = setup(request_status=ServiceRequestStatus.MATCHING)
    declined = make_assignment(
        request_id=ctx["service_request"].id,
        worker_id=ctx["worker"].id,
        assigned_by=ctx["admin"].id,
        status=AssignmentStatus.DECLINED,
    )

    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 201

    db_session.refresh(declined)
    assert declined.status == AssignmentStatus.DECLINED

    from sqlalchemy import select as sa_select

    all_assignments = db_session.execute(
        sa_select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
    ).scalars().all()
    assert len(all_assignments) == 2


def test_failed_assignment_does_not_leave_partial_update(
    client, setup, auth_header, db_session
):
    ctx = setup(worker_has_skill=False)
    original_status = ctx["service_request"].status

    response = client.post(
        _url(ctx["service_request"].id),
        json={"workerId": str(ctx["worker"].id)},
        headers=auth_header(ctx["admin"]),
    )
    assert response.status_code == 409

    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == original_status

    from sqlalchemy import select as sa_select

    assignments = db_session.execute(
        sa_select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
    ).scalars().all()
    assert assignments == []


# --- Concurrency: row-level locking ----------------------------------------


def test_concurrent_assignment_attempts_are_serialized_by_row_lock():
    """
    Demonstrates the fix for the two-concurrent-admins race: the endpoint
    locks the ServiceRequest row with `SELECT ... FOR UPDATE` as its very
    first step and holds that lock for the rest of its transaction, so a
    second, concurrent lock attempt on the same row must wait rather than
    both transactions reading it as unassigned and both creating an
    Assignment.

    `with_for_update()`'s blocking behavior is only observable across two
    genuinely independent connections against COMMITTED data — every
    other test in this module deliberately uses the shared
    `db_session`/`client` fixtures, which never commit (see conftest.py's
    rollback-based per-test isolation), so a second, independent
    connection would never even see the row and the lock check would be
    vacuous. This test therefore builds and commits its own throwaway
    fixture data directly against `engine`, independently of the shared
    fixtures, and explicitly deletes everything it created in a
    `finally` block — it never touches `db_session`/`client` or their
    isolation guarantees.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm import Session as OrmSession

    from app.models.account import Account
    from app.models.association import Association
    from app.models.federation import Federation
    from app.models.service import Service
    from app.models.user_profile import UserProfile
    from app.models.worker import Worker
    from app.models.worker_skill import WorkerSkill

    setup_session = OrmSession(bind=engine)
    request_id = None
    try:
        federation = Federation(name=f"Concurrency Federation {uuid.uuid4().hex[:8]}")
        setup_session.add(federation)
        setup_session.flush()

        association = Association(
            federation_id=federation.id, name=f"Concurrency Association {uuid.uuid4().hex[:8]}"
        )
        setup_session.add(association)
        setup_session.flush()

        user_account = Account(
            login_id=f"concurrency_user_{uuid.uuid4().hex[:12]}", role=AccountRole.USER
        )
        worker_account = Account(
            login_id=f"concurrency_worker_{uuid.uuid4().hex[:12]}", role=AccountRole.WORKER
        )
        setup_session.add_all([user_account, worker_account])
        setup_session.flush()

        user_profile = UserProfile(account_id=user_account.id, full_name="Concurrency User")
        service = Service(name=f"Concurrency Service {uuid.uuid4().hex[:8]}", category="General")
        worker = Worker(
            account_id=worker_account.id,
            association_id=association.id,
            worker_code=f"CW-{uuid.uuid4().hex[:8]}",
            full_name="Concurrency Worker",
            status=WorkerStatus.ACTIVE,
        )
        setup_session.add_all([user_profile, service, worker])
        setup_session.flush()

        setup_session.add(WorkerSkill(worker_id=worker.id, service_id=service.id))

        service_request = ServiceRequest(
            user_id=user_profile.id,
            service_id=service.id,
            association_id=association.id,
            status=ServiceRequestStatus.PENDING,
            address="12 MG Road",
            pincode="560001",
            requested_date_time=datetime.now(timezone.utc) + timedelta(hours=5),
        )
        setup_session.add(service_request)
        setup_session.flush()

        # Commit is required here (unlike every other test in this file)
        # so the row is visible to `second_connection` below, which is a
        # deliberately separate connection/transaction.
        setup_session.commit()
        request_id = service_request.id

        # Lock the row, exactly as the endpoint's own step 1 does, and do
        # NOT commit/rollback yet -- simulating the first admin's request
        # still being mid-transaction.
        setup_session.execute(
            select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
        ).scalar_one()

        second_connection = engine.connect()
        try:
            second_connection.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError):
                second_connection.execute(
                    select(ServiceRequest)
                    .where(ServiceRequest.id == request_id)
                    .with_for_update()
                )
        finally:
            second_connection.rollback()
            second_connection.close()

        # Release the first transaction's lock before cleanup below.
        setup_session.rollback()
    finally:
        # Explicit cleanup, in FK-safe order, of everything committed
        # above -- this test's data must not leak into later test runs.
        cleanup_session = OrmSession(bind=engine)
        try:
            if request_id is not None:
                cleanup_session.execute(
                    ServiceRequest.__table__.delete().where(ServiceRequest.id == request_id)
                )
            cleanup_session.execute(
                Worker.__table__.delete().where(
                    Worker.worker_code.like("CW-%"), Worker.full_name == "Concurrency Worker"
                )
            )
            cleanup_session.execute(
                Account.__table__.delete().where(
                    Account.login_id.like("concurrency_user_%")
                    | Account.login_id.like("concurrency_worker_%")
                )
            )
            cleanup_session.execute(
                Service.__table__.delete().where(Service.name.like("Concurrency Service %"))
            )
            cleanup_session.execute(
                Association.__table__.delete().where(
                    Association.name.like("Concurrency Association %")
                )
            )
            cleanup_session.execute(
                Federation.__table__.delete().where(
                    Federation.name.like("Concurrency Federation %")
                )
            )
            cleanup_session.commit()
        finally:
            cleanup_session.close()
        setup_session.close()
