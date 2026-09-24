"""
Tests for the Phase 5E-F-A worker assignment-response lifecycle:
`POST /assignments/{assignment_id}/accept`, `.../decline`, `.../cancel`.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.database import engine
from app.models.assignment import Assignment
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus, WorkerStatus

ACCEPT_URL = "/assignments/{assignment_id}/accept"
DECLINE_URL = "/assignments/{assignment_id}/decline"
CANCEL_URL = "/assignments/{assignment_id}/cancel"


def _url(template: str, assignment_id) -> str:
    return template.format(assignment_id=assignment_id)


@pytest.fixture()
def build(
    make_federation,
    make_association,
    make_account,
    make_service,
    make_user_profile,
    make_worker,
    make_worker_skill,
    make_service_request,
    make_assignment,
    db_session,
):
    """
    Factory fixture: build one federation/association, a USER with a
    request, an eligible ACTIVE WORKER (skilled in the request's
    service), an ASSOCIATION_ADMIN (used as `assigned_by`), and one
    Assignment for that worker/request pair, with the given
    `assignment_status`/`request_status` combination. Returns a dict of
    everything a test might need.
    """

    def _build(
        *,
        assignment_status: AssignmentStatus = AssignmentStatus.PENDING_RESPONSE,
        request_status: ServiceRequestStatus = ServiceRequestStatus.ASSIGNED,
        responded_at=None,
    ):
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
        worker = make_worker(account_id=worker_account.id, association_id=association.id)
        make_worker_skill(worker_id=worker.id, service_id=service.id)

        assignment = make_assignment(
            request_id=service_request.id,
            worker_id=worker.id,
            assigned_by=admin.id,
            status=assignment_status,
        )
        if responded_at is not None:
            assignment.responded_at = responded_at
            db_session.flush()

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
            "assignment": assignment,
        }

    return _build


# ============================================================ ACCEPT ======


def test_valid_worker_can_accept_own_pending_assignment(client, build, auth_header, db_session):
    ctx = build()
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AssignmentStatus.ACCEPTED.value

    db_session.refresh(ctx["assignment"])
    db_session.refresh(ctx["service_request"])
    assert ctx["assignment"].status == AssignmentStatus.ACCEPTED
    assert ctx["service_request"].status == ServiceRequestStatus.ACCEPTED


def test_accept_response_contains_correct_status(client, build, auth_header):
    ctx = build()
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    body = response.json()
    assert body["status"] == "ACCEPTED"
    assert body["id"] == str(ctx["assignment"].id)
    assert body["respondedAt"] is not None
    assert set(body.keys()) == {
        "id", "requestId", "workerId", "assignedBy", "status",
        "assignedAt", "respondedAt", "updatedAt",
    }


def test_another_worker_cannot_accept(client, build, make_account, make_worker, auth_header):
    ctx = build()
    other_worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=other_worker_account.id, association_id=ctx["association"].id)

    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(other_worker_account)
    )
    assert response.status_code == 404


def test_accept_user_role_forbidden(client, build, auth_header):
    ctx = build()
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 403


def test_accept_association_admin_role_forbidden(client, build, auth_header):
    ctx = build()
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["admin"])
    )
    assert response.status_code == 403


def test_accept_federation_admin_role_forbidden(client, build, make_account, auth_header):
    ctx = build()
    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=ctx["federation"].id)
    response = client.post(_url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(fed_admin))
    assert response.status_code == 403


def test_accept_unauthenticated_returns_401(client, build):
    ctx = build()
    response = client.post(_url(ACCEPT_URL, ctx["assignment"].id))
    assert response.status_code == 401


def test_accept_already_accepted_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_accept_declined_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.DECLINED, request_status=ServiceRequestStatus.MATCHING
    )
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_accept_cancelled_by_worker_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.CANCELLED_BY_WORKER,
        request_status=ServiceRequestStatus.MATCHING,
    )
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_accept_invalid_request_state_returns_409(client, build, auth_header):
    # Assignment is PENDING_RESPONSE (the normally-required state) but the
    # ServiceRequest itself is not ASSIGNED -- a data state that shouldn't
    # arise through normal use, but the endpoint must still reject it.
    ctx = build(
        assignment_status=AssignmentStatus.PENDING_RESPONSE,
        request_status=ServiceRequestStatus.PENDING,
    )
    response = client.post(
        _url(ACCEPT_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_accept_nonexistent_assignment_returns_404(client, build, auth_header):
    ctx = build()
    response = client.post(_url(ACCEPT_URL, uuid.uuid4()), headers=auth_header(ctx["worker_account"]))
    assert response.status_code == 404


def test_accept_malformed_uuid_returns_422(client, build, auth_header):
    ctx = build()
    response = client.post(_url(ACCEPT_URL, "not-a-uuid"), headers=auth_header(ctx["worker_account"]))
    assert response.status_code == 422


def test_accept_worker_without_profile_returns_404(client, make_account, auth_header):
    account = make_account(role=AccountRole.WORKER)
    response = client.post(_url(ACCEPT_URL, uuid.uuid4()), headers=auth_header(account))
    assert response.status_code == 404


# =========================================================== DECLINE ======


def test_valid_worker_can_decline_own_pending_assignment(client, build, auth_header, db_session):
    ctx = build()
    response = client.post(
        _url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == AssignmentStatus.DECLINED.value

    db_session.refresh(ctx["assignment"])
    db_session.refresh(ctx["service_request"])
    assert ctx["assignment"].status == AssignmentStatus.DECLINED
    assert ctx["service_request"].status == ServiceRequestStatus.MATCHING


def test_decline_assignment_row_remains(client, build, auth_header, db_session):
    ctx = build()
    client.post(_url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))

    row = db_session.get(Assignment, ctx["assignment"].id)
    assert row is not None
    assert row.status == AssignmentStatus.DECLINED


def test_another_worker_cannot_decline(client, build, make_account, make_worker, auth_header):
    ctx = build()
    other_worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=other_worker_account.id, association_id=ctx["association"].id)

    response = client.post(
        _url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(other_worker_account)
    )
    assert response.status_code == 404


def test_decline_already_accepted_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    response = client.post(
        _url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_decline_already_declined_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.DECLINED, request_status=ServiceRequestStatus.MATCHING
    )
    response = client.post(
        _url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_decline_unauthenticated_returns_401(client, build):
    ctx = build()
    response = client.post(_url(DECLINE_URL, ctx["assignment"].id))
    assert response.status_code == 401


@pytest.mark.parametrize("role_key", ["user_account", "admin"])
def test_decline_wrong_role_forbidden(client, build, auth_header, role_key):
    ctx = build()
    response = client.post(_url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(ctx[role_key]))
    assert response.status_code == 403


def test_decline_federation_admin_forbidden(client, build, make_account, auth_header):
    ctx = build()
    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=ctx["federation"].id)
    response = client.post(_url(DECLINE_URL, ctx["assignment"].id), headers=auth_header(fed_admin))
    assert response.status_code == 403


# ============================================================ CANCEL ======


def test_valid_worker_can_cancel_own_accepted_assignment(client, build, auth_header, db_session):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    response = client.post(
        _url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == AssignmentStatus.CANCELLED_BY_WORKER.value

    db_session.refresh(ctx["assignment"])
    db_session.refresh(ctx["service_request"])
    assert ctx["assignment"].status == AssignmentStatus.CANCELLED_BY_WORKER
    assert ctx["service_request"].status == ServiceRequestStatus.MATCHING


def test_cancel_assignment_row_remains(client, build, auth_header, db_session):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    client.post(_url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))

    row = db_session.get(Assignment, ctx["assignment"].id)
    assert row is not None
    assert row.status == AssignmentStatus.CANCELLED_BY_WORKER


def test_cancel_pending_response_assignment_returns_409(client, build, auth_header):
    ctx = build()  # default: PENDING_RESPONSE / ASSIGNED
    response = client.post(
        _url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_cancel_declined_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.DECLINED, request_status=ServiceRequestStatus.MATCHING
    )
    response = client.post(
        _url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_cancel_completed_assignment_returns_409(client, build, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.COMPLETED,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
    )
    response = client.post(
        _url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_another_worker_cannot_cancel(client, build, make_account, make_worker, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    other_worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=other_worker_account.id, association_id=ctx["association"].id)

    response = client.post(
        _url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(other_worker_account)
    )
    assert response.status_code == 404


def test_cancel_unauthenticated_returns_401(client, build):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    response = client.post(_url(CANCEL_URL, ctx["assignment"].id))
    assert response.status_code == 401


@pytest.mark.parametrize("role_key", ["user_account", "admin"])
def test_cancel_wrong_role_forbidden(client, build, auth_header, role_key):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    response = client.post(_url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(ctx[role_key]))
    assert response.status_code == 403


def test_cancel_federation_admin_forbidden(client, build, make_account, auth_header):
    ctx = build(
        assignment_status=AssignmentStatus.ACCEPTED, request_status=ServiceRequestStatus.ACCEPTED
    )
    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=ctx["federation"].id)
    response = client.post(_url(CANCEL_URL, ctx["assignment"].id), headers=auth_header(fed_admin))
    assert response.status_code == 403


# ================================================ HISTORY / REASSIGNMENT ===


def test_decline_reassign_accept_cancel_preserves_full_history(
    client, build, make_account, make_worker, auth_header, db_session
):
    """
    End-to-end narrative: Worker A declines Assignment #1 -> request goes
    MATCHING -> the Association Admin creates Assignment #2 for Worker B
    via the existing Phase 5E-E endpoint -> request goes back to ASSIGNED
    -> Worker B accepts, then cancels Assignment #2 -> request goes back
    to MATCHING. Assignment #1 must remain DECLINED and completely
    unchanged throughout.
    """
    ctx = build()  # Assignment #1: PENDING_RESPONSE, request ASSIGNED
    assignment_1 = ctx["assignment"]
    assignment_1_assigned_at = assignment_1.assigned_at

    # Worker A declines Assignment #1.
    decline_response = client.post(
        _url(DECLINE_URL, assignment_1.id), headers=auth_header(ctx["worker_account"])
    )
    assert decline_response.status_code == 200

    db_session.refresh(assignment_1)
    db_session.refresh(ctx["service_request"])
    assert assignment_1.status == AssignmentStatus.DECLINED
    assert ctx["service_request"].status == ServiceRequestStatus.MATCHING

    # Association Admin creates Assignment #2 for a different, eligible
    # Worker B, through the existing Phase 5E-E endpoint.
    worker_b_account = make_account(role=AccountRole.WORKER)
    worker_b = make_worker(account_id=worker_b_account.id, association_id=ctx["association"].id)
    from app.models.worker_skill import WorkerSkill

    db_session.add(WorkerSkill(worker_id=worker_b.id, service_id=ctx["service"].id))
    db_session.flush()

    create_response = client.post(
        f"/associations/me/requests/{ctx['service_request'].id}/assignments",
        json={"workerId": str(worker_b.id)},
        headers=auth_header(ctx["admin"]),
    )
    assert create_response.status_code == 201
    assignment_2_id = uuid.UUID(create_response.json()["id"])
    assert create_response.json()["status"] == AssignmentStatus.PENDING_RESPONSE.value

    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.ASSIGNED

    # Assignment #1 must remain unchanged by the new assignment.
    db_session.refresh(assignment_1)
    assert assignment_1.status == AssignmentStatus.DECLINED
    assert assignment_1.assigned_at == assignment_1_assigned_at

    # Worker B accepts Assignment #2.
    accept_response = client.post(
        _url(ACCEPT_URL, assignment_2_id), headers=auth_header(worker_b_account)
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == AssignmentStatus.ACCEPTED.value

    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.ACCEPTED

    # Worker B then cancels Assignment #2.
    cancel_response = client.post(
        _url(CANCEL_URL, assignment_2_id), headers=auth_header(worker_b_account)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == AssignmentStatus.CANCELLED_BY_WORKER.value

    assignment_2 = db_session.get(Assignment, assignment_2_id)
    db_session.refresh(ctx["service_request"])
    assert assignment_2.status == AssignmentStatus.CANCELLED_BY_WORKER
    assert ctx["service_request"].status == ServiceRequestStatus.MATCHING

    # Assignment #1 is still DECLINED and untouched by any of this.
    db_session.refresh(assignment_1)
    assert assignment_1.status == AssignmentStatus.DECLINED
    assert assignment_1.assigned_at == assignment_1_assigned_at

    # Both historical rows exist -- nothing was deleted.
    all_assignments = db_session.execute(
        select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
    ).scalars().all()
    assert {a.id for a in all_assignments} == {assignment_1.id, assignment_2_id}


# ========================================================= CONCURRENCY ====


def test_concurrent_mutations_on_same_assignment_are_serialized_by_row_lock():
    """
    Demonstrates the row-locking fix: every lifecycle mutation
    (accept/decline/cancel) locks the Assignment row with
    `SELECT ... FOR UPDATE` as its very first step, before checking
    ownership or state, and holds that lock for the rest of its
    transaction.

    Because all three mutations acquire the identical lock on the same
    Assignment row as step 1, this single row-lock mechanism uniformly
    serializes every conflicting pair the spec lists (accept vs decline,
    accept vs cancel, accept vs accept, decline vs decline, cancel vs
    cancel) -- whichever transaction locks the row first proceeds to
    completion; a second, concurrent transaction targeting the same
    row cannot even read its current state until the first finishes, at
    which point it observes the already-updated status and is correctly
    rejected with 409 rather than racing to also apply a transition.

    As in the Phase 5E-E concurrency test, `with_for_update()`'s
    blocking behavior is only observable across two genuinely
    independent connections against COMMITTED data -- the shared
    `db_session`/`client` fixtures never commit (rollback-based per-test
    isolation), so this test builds and commits its own throwaway
    fixture data directly against `engine`, and explicitly cleans it up
    in a `finally` block.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm import Session as OrmSession

    from app.models.account import Account
    from app.models.association import Association
    from app.models.federation import Federation
    from app.models.service import Service
    from app.models.service_request import ServiceRequest
    from app.models.user_profile import UserProfile
    from app.models.worker import Worker
    from app.models.worker_skill import WorkerSkill

    setup_session = OrmSession(bind=engine)
    assignment_id = None
    ids: dict = {}
    try:
        federation = Federation(name=f"Lifecycle Federation {uuid.uuid4().hex[:8]}")
        setup_session.add(federation)
        setup_session.flush()

        association = Association(
            federation_id=federation.id, name=f"Lifecycle Association {uuid.uuid4().hex[:8]}"
        )
        setup_session.add(association)
        setup_session.flush()

        admin_account = Account(
            login_id=f"lifecycle_admin_{uuid.uuid4().hex[:12]}",
            role=AccountRole.ASSOCIATION_ADMIN,
            association_id=association.id,
        )
        user_account = Account(
            login_id=f"lifecycle_user_{uuid.uuid4().hex[:12]}", role=AccountRole.USER
        )
        worker_account = Account(
            login_id=f"lifecycle_worker_{uuid.uuid4().hex[:12]}", role=AccountRole.WORKER
        )
        setup_session.add_all([admin_account, user_account, worker_account])
        setup_session.flush()

        user_profile = UserProfile(account_id=user_account.id, full_name="Lifecycle User")
        service = Service(name=f"Lifecycle Service {uuid.uuid4().hex[:8]}", category="General")
        worker = Worker(
            account_id=worker_account.id,
            association_id=association.id,
            worker_code=f"LW-{uuid.uuid4().hex[:8]}",
            full_name="Lifecycle Worker",
            status=WorkerStatus.ACTIVE,
        )
        setup_session.add_all([user_profile, service, worker])
        setup_session.flush()

        setup_session.add(WorkerSkill(worker_id=worker.id, service_id=service.id))

        service_request = ServiceRequest(
            user_id=user_profile.id,
            service_id=service.id,
            association_id=association.id,
            status=ServiceRequestStatus.ASSIGNED,
            address="12 MG Road",
            pincode="560001",
            requested_date_time=datetime.now(timezone.utc) + timedelta(hours=5),
        )
        setup_session.add(service_request)
        setup_session.flush()

        assignment = Assignment(
            request_id=service_request.id,
            worker_id=worker.id,
            assigned_by=admin_account.id,
            status=AssignmentStatus.PENDING_RESPONSE,
        )
        setup_session.add(assignment)
        setup_session.flush()

        # Commit so the row is visible to `second_connection` below.
        setup_session.commit()
        assignment_id = assignment.id
        ids = {
            "assignment_id": assignment.id,
            "service_request_id": service_request.id,
            "worker_id": worker.id,
            "account_ids": [admin_account.id, user_account.id, worker_account.id],
            "service_id": service.id,
            "association_id": association.id,
            "federation_id": federation.id,
        }

        # Lock the Assignment row, exactly as step 1 of every lifecycle
        # mutation does, and deliberately do NOT commit/rollback yet --
        # simulating a first worker request (e.g. accept) still being
        # mid-transaction.
        setup_session.execute(
            select(Assignment).where(Assignment.id == assignment_id).with_for_update()
        ).scalar_one()

        second_connection = engine.connect()
        try:
            second_connection.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError):
                second_connection.execute(
                    select(Assignment).where(Assignment.id == assignment_id).with_for_update()
                )
        finally:
            second_connection.rollback()
            second_connection.close()

        setup_session.rollback()
    finally:
        cleanup_session = OrmSession(bind=engine)
        try:
            # Exact-id deletes, in FK-safe order (children before
            # parents), so nothing this test committed leaks into later
            # test runs.
            if ids.get("assignment_id") is not None:
                cleanup_session.execute(
                    Assignment.__table__.delete().where(Assignment.id == ids["assignment_id"])
                )
            if ids.get("service_request_id") is not None:
                cleanup_session.execute(
                    ServiceRequest.__table__.delete().where(
                        ServiceRequest.id == ids["service_request_id"]
                    )
                )
            if ids.get("worker_id") is not None:
                cleanup_session.execute(
                    Worker.__table__.delete().where(Worker.id == ids["worker_id"])
                )
            if ids.get("account_ids"):
                cleanup_session.execute(
                    Account.__table__.delete().where(Account.id.in_(ids["account_ids"]))
                )
            if ids.get("service_id") is not None:
                cleanup_session.execute(
                    Service.__table__.delete().where(Service.id == ids["service_id"])
                )
            if ids.get("association_id") is not None:
                cleanup_session.execute(
                    Association.__table__.delete().where(
                        Association.id == ids["association_id"]
                    )
                )
            if ids.get("federation_id") is not None:
                cleanup_session.execute(
                    Federation.__table__.delete().where(Federation.id == ids["federation_id"])
                )
            cleanup_session.commit()
        finally:
            cleanup_session.close()
        setup_session.close()
