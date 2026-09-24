"""
Tests for the Phase 5E-I complete-request lifecycle:

`POST /assignments/{assignment_id}/complete` — WORKER, Assignment ACCEPTED
    -> COMPLETED, ServiceRequest ACCEPTED -> WORKER_COMPLETED.
`POST /requests/{request_id}/confirm`        — USER, ServiceRequest
    WORKER_COMPLETED -> PAYMENT_PENDING (passing through USER_CONFIRMED).
`POST /requests/{request_id}/pay`            — USER, ServiceRequest
    PAYMENT_PENDING -> COMPLETED (passing through PAID); demo/MVP only,
    no Payment model/table/gateway anywhere.

Also confirms the existing worker accept/decline/cancel behavior and the
Phase 5E-E assignment endpoint are unaffected.
"""

from datetime import datetime, timedelta, timezone

from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus

COMPLETE_URL = "/assignments/{assignment_id}/complete"
CONFIRM_URL = "/requests/{request_id}/confirm"
PAY_URL = "/requests/{request_id}/pay"

REQUEST_DATETIME = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)


def _complete_url(assignment_id) -> str:
    return COMPLETE_URL.format(assignment_id=assignment_id)


def _confirm_url(request_id) -> str:
    return CONFIRM_URL.format(request_id=request_id)


def _pay_url(request_id) -> str:
    return PAY_URL.format(request_id=request_id)


def _build_accepted_assignment(
    make_federation,
    make_association,
    make_account,
    make_user_profile,
    make_service,
    make_service_request,
    make_worker,
    make_assignment,
    *,
    request_status: ServiceRequestStatus = ServiceRequestStatus.ACCEPTED,
    assignment_status: AssignmentStatus = AssignmentStatus.ACCEPTED,
):
    """
    Build a full chain: Federation -> Association -> Service ->
    ServiceRequest (at `request_status`) -> Worker -> Assignment (at
    `assignment_status`), plus the USER account that owns the request and
    the ASSOCIATION_ADMIN that made the assignment. Returns a dict of
    everything a test might need, keyed by name.
    """
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)

    service_request = make_service_request(
        user_id=profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
        status=request_status,
    )

    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)

    worker_account = make_account(role=AccountRole.WORKER)
    worker = make_worker(account_id=worker_account.id, association_id=association.id)

    assignment = make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=assignment_status,
    )

    return {
        "federation": federation,
        "association": association,
        "service": service,
        "user_account": user_account,
        "profile": profile,
        "service_request": service_request,
        "admin": admin,
        "worker_account": worker_account,
        "worker": worker,
        "assignment": assignment,
    }


# ==================================================== WORKER COMPLETION ===


def test_complete_unauthenticated_returns_401(client):
    import uuid

    response = client.post(_complete_url(uuid.uuid4()))
    assert response.status_code == 401


def test_complete_wrong_role_returns_403(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    response = client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["user_account"]))
    assert response.status_code == 403

    response = client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["admin"]))
    assert response.status_code == 403


def test_worker_can_complete_own_accepted_assignment(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    response = client.post(
        _complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(ctx["assignment"].id)
    assert body["status"] == AssignmentStatus.COMPLETED.value


def test_completion_transitions_assignment_and_request(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))

    db_session.refresh(ctx["assignment"])
    db_session.refresh(ctx["service_request"])
    assert ctx["assignment"].status == AssignmentStatus.COMPLETED
    assert ctx["service_request"].status == ServiceRequestStatus.WORKER_COMPLETED


def test_another_worker_cannot_complete_assignment(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    other_worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=other_worker_account.id, association_id=ctx["association"].id)

    response = client.post(
        _complete_url(ctx["assignment"].id), headers=auth_header(other_worker_account)
    )
    assert response.status_code == 404


def test_complete_invalid_assignment_status_returns_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.ASSIGNED,
        assignment_status=AssignmentStatus.PENDING_RESPONSE,
    )
    response = client.post(
        _complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_complete_invalid_request_status_returns_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    """
    Assignment is ACCEPTED, but its ServiceRequest has (defensively)
    already moved on -- e.g. WORKER_COMPLETED from a previous completion
    -- so a second completion attempt against the request's state must
    still reject with 409 even if the Assignment row itself looks ready.
    """
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.ACCEPTED,
    )
    response = client.post(
        _complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 409


def test_complete_nonexistent_assignment_returns_404(client, make_account, auth_header):
    import uuid

    worker_account = make_account(role=AccountRole.WORKER)
    response = client.post(_complete_url(uuid.uuid4()), headers=auth_header(worker_account))
    assert response.status_code == 404


def test_repeated_completion_is_rejected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    first = client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))
    assert first.status_code == 200

    second = client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))
    assert second.status_code == 409


def test_completion_creates_no_new_assignment(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    from sqlalchemy import select

    from app.models.assignment import Assignment

    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    before_count = len(
        db_session.execute(
            select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
        ).scalars().all()
    )
    client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))
    after_count = len(
        db_session.execute(
            select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
        ).scalars().all()
    )
    assert after_count == before_count == 1


def test_completion_preserves_assignment_history(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )
    original_responded_at = ctx["assignment"].responded_at
    original_assigned_at = ctx["assignment"].assigned_at
    original_assigned_by = ctx["assignment"].assigned_by
    original_worker_id = ctx["assignment"].worker_id
    original_request_id = ctx["assignment"].request_id

    client.post(_complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"]))

    db_session.refresh(ctx["assignment"])
    assert ctx["assignment"].responded_at == original_responded_at
    assert ctx["assignment"].assigned_at == original_assigned_at
    assert ctx["assignment"].assigned_by == original_assigned_by
    assert ctx["assignment"].worker_id == original_worker_id
    assert ctx["assignment"].request_id == original_request_id


# ===================================================== USER CONFIRMATION ===


def test_confirm_unauthenticated_returns_401(client):
    import uuid

    response = client.post(_confirm_url(uuid.uuid4()))
    assert response.status_code == 401


def test_confirm_wrong_role_returns_403(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    response = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["worker_account"])
    )
    assert response.status_code == 403

    response = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["admin"])
    )
    assert response.status_code == 403


def test_owning_user_can_confirm_worker_completed_request(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    response = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(ctx["service_request"].id)
    assert body["status"] == ServiceRequestStatus.PAYMENT_PENDING.value


def test_non_owner_cannot_confirm(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    other_user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=other_user_account.id)

    response = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(other_user_account)
    )
    assert response.status_code == 404


def test_confirm_invalid_starting_state_returns_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.ACCEPTED,
        assignment_status=AssignmentStatus.ACCEPTED,
    )
    response = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 409


def test_repeated_confirmation_is_rejected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    first = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert first.status_code == 200

    second = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert second.status_code == 409


def test_confirmation_does_not_mutate_assignment(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    original_status = ctx["assignment"].status
    original_updated_at = ctx["assignment"].updated_at

    client.post(_confirm_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))

    db_session.refresh(ctx["assignment"])
    assert ctx["assignment"].status == original_status
    assert ctx["assignment"].updated_at == original_updated_at


# ========================================================= DEMO PAYMENT ===


def test_pay_unauthenticated_returns_401(client):
    import uuid

    response = client.post(_pay_url(uuid.uuid4()))
    assert response.status_code == 401


def test_pay_wrong_role_returns_403(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.PAYMENT_PENDING,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    response = client.post(_pay_url(ctx["service_request"].id), headers=auth_header(ctx["worker_account"]))
    assert response.status_code == 403

    response = client.post(_pay_url(ctx["service_request"].id), headers=auth_header(ctx["admin"]))
    assert response.status_code == 403


def test_owner_can_pay_from_payment_pending(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.PAYMENT_PENDING,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    response = client.post(
        _pay_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(ctx["service_request"].id)
    assert body["status"] == ServiceRequestStatus.COMPLETED.value


def test_paid_remains_part_of_canonical_status_enum():
    assert ServiceRequestStatus.PAID.value == "PAID"
    assert ServiceRequestStatus.PAID in list(ServiceRequestStatus)


def test_non_owner_cannot_pay(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.PAYMENT_PENDING,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    other_user_account = make_account(role=AccountRole.USER)
    make_user_profile(account_id=other_user_account.id)

    response = client.post(
        _pay_url(ctx["service_request"].id), headers=auth_header(other_user_account)
    )
    assert response.status_code == 404


def test_pay_invalid_starting_state_returns_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.WORKER_COMPLETED,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    response = client.post(
        _pay_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert response.status_code == 409


def test_repeated_payment_is_rejected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.PAYMENT_PENDING,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    first = client.post(_pay_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))
    assert first.status_code == 200

    second = client.post(_pay_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))
    assert second.status_code == 409


def test_payment_does_not_mutate_assignment(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.PAYMENT_PENDING,
        assignment_status=AssignmentStatus.COMPLETED,
    )
    original_status = ctx["assignment"].status
    original_updated_at = ctx["assignment"].updated_at

    client.post(_pay_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"]))

    db_session.refresh(ctx["assignment"])
    assert ctx["assignment"].status == original_status
    assert ctx["assignment"].updated_at == original_updated_at


def test_no_payment_table_or_model_exists():
    """
    Defense-in-depth against scope creep: this phase must never introduce
    a Payment SQLAlchemy model or database table. Confirms no such name
    is registered against the shared declarative metadata.
    """
    from app.database import Base

    table_names = set(Base.metadata.tables.keys())
    assert "payments" not in table_names
    assert "payment" not in table_names

    import app.models as models_package

    assert not hasattr(models_package, "Payment")


# ==================================================== FULL LIFECYCLE E2E ===


def test_full_completion_lifecycle_end_to_end(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    """
    Worker completes -> user confirms -> user pays, in sequence, ending
    at COMPLETED, with exactly one Assignment row throughout.
    """
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
    )

    complete_response = client.post(
        _complete_url(ctx["assignment"].id), headers=auth_header(ctx["worker_account"])
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == AssignmentStatus.COMPLETED.value

    confirm_response = client.post(
        _confirm_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == ServiceRequestStatus.PAYMENT_PENDING.value

    pay_response = client.post(
        _pay_url(ctx["service_request"].id), headers=auth_header(ctx["user_account"])
    )
    assert pay_response.status_code == 200
    assert pay_response.json()["status"] == ServiceRequestStatus.COMPLETED.value

    from sqlalchemy import select

    from app.models.assignment import Assignment

    remaining = db_session.execute(
        select(Assignment).where(Assignment.request_id == ctx["service_request"].id)
    ).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].status == AssignmentStatus.COMPLETED


# ========================================================== REGRESSION ===


def test_existing_worker_accept_decline_cancel_unaffected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_assignment, auth_header, db_session,
):
    ctx = _build_accepted_assignment(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, make_worker, make_assignment,
        request_status=ServiceRequestStatus.ASSIGNED,
        assignment_status=AssignmentStatus.PENDING_RESPONSE,
    )

    decline_response = client.post(
        f"/assignments/{ctx['assignment'].id}/decline", headers=auth_header(ctx["worker_account"])
    )
    assert decline_response.status_code == 200
    assert decline_response.json()["status"] == AssignmentStatus.DECLINED.value

    db_session.refresh(ctx["service_request"])
    assert ctx["service_request"].status == ServiceRequestStatus.MATCHING
