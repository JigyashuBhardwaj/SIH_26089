"""
Tests for the Phase 5E-H read-only candidate discovery route:
`GET /associations/me/requests/{request_id}/candidates`.

Covers authorization, association isolation, request-state gating, the
four worker-eligibility rules (association/active/skill/availability),
the deterministic (non-weighted) ranking order, response shape, and
pagination — plus a regression check that the Phase 5E-E assignment
endpoint's own behavior is untouched.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.enums import (
    AccountRole,
    AssignmentStatus,
    ServiceRequestStatus,
    WorkerStatus,
)

CANDIDATES_URL = "/associations/me/requests/{request_id}/candidates"
ASSIGNMENTS_URL = "/associations/me/requests/{request_id}/assignments"

REQUEST_DATETIME = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)


def _url(request_id) -> str:
    return CANDIDATES_URL.format(request_id=request_id)


def _setup_request(
    make_federation,
    make_association,
    make_account,
    make_user_profile,
    make_service,
    make_service_request,
    *,
    requested_date_time=REQUEST_DATETIME,
    pincode: str = "560001",
    status: ServiceRequestStatus = ServiceRequestStatus.PENDING,
):
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    user_account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=user_account.id)
    # `Service.name` is unique, and `_setup_request` may be called more
    # than once within a single test (e.g. looping over several
    # ServiceRequest statuses) -- let `make_service` generate its own
    # unique name rather than colliding on a fixed "Plumbing" every time.
    service = make_service()
    service_request = make_service_request(
        user_id=profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=requested_date_time,
        pincode=pincode,
        status=status,
    )
    admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=association.id)
    return federation, association, service, service_request, admin


def _make_eligible_worker(
    make_account,
    make_worker,
    make_worker_skill,
    *,
    association_id,
    service_id,
    full_name: str = "Eligible Worker",
    status: WorkerStatus = WorkerStatus.ACTIVE,
    pincode: str = "560001",
    rating=Decimal("4.00"),
    total_jobs_completed: int = 0,
):
    account = make_account(role=AccountRole.WORKER)
    worker = make_worker(
        account_id=account.id,
        association_id=association_id,
        full_name=full_name,
        status=status,
        pincode=pincode,
        rating=rating,
        total_jobs_completed=total_jobs_completed,
    )
    make_worker_skill(worker_id=worker.id, service_id=service_id)
    return account, worker


# ===================================================== AUTHORIZATION ===


def test_unauthenticated_returns_401(client, make_federation, make_association, make_service_request):
    import uuid

    response = client.get(_url(uuid.uuid4()))
    assert response.status_code == 401


def test_user_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, _ = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    other_user = make_account(role=AccountRole.USER)
    make_user_profile(account_id=other_user.id)
    response = client.get(_url(service_request.id), headers=auth_header(other_user))
    assert response.status_code == 403


def test_worker_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, auth_header,
):
    federation, association, service, service_request, _ = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    worker_account = make_account(role=AccountRole.WORKER)
    make_worker(account_id=worker_account.id, association_id=association.id)
    response = client.get(_url(service_request.id), headers=auth_header(worker_account))
    assert response.status_code == 403


def test_federation_admin_role_forbidden(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    federation, association, service, service_request, _ = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    fed_admin = make_account(role=AccountRole.FEDERATION_ADMIN, federation_id=federation.id)
    response = client.get(_url(service_request.id), headers=auth_header(fed_admin))
    assert response.status_code == 403


def test_association_admin_allowed(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert response.status_code == 200


# =================================================== ASSOCIATION ISOLATION ===


def test_admin_cannot_retrieve_candidates_for_another_association(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, _ = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    other_federation = make_federation()
    other_association = make_association(federation_id=other_federation.id)
    other_admin = make_account(role=AccountRole.ASSOCIATION_ADMIN, association_id=other_association.id)

    response = client.get(_url(service_request.id), headers=auth_header(other_admin))
    assert response.status_code == 404


def test_workers_from_another_association_never_appear(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    federation, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="In Association",
    )
    other_association = make_association(federation_id=federation.id)
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=other_association.id, service_id=service.id, full_name="Other Association",
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    body = response.json()
    names = [item["fullName"] for item in body["items"]]
    assert "In Association" in names
    assert "Other Association" not in names


# ======================================================= REQUEST STATE ===


def test_pending_request_allows_candidate_discovery(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.PENDING,
    )
    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert response.status_code == 200


def test_matching_request_allows_candidate_discovery(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.MATCHING,
    )
    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert response.status_code == 200


def test_assigned_request_returns_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ASSIGNED,
    )
    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert response.status_code == 409


def test_accepted_request_returns_409(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    _, _, _, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.ACCEPTED,
    )
    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert response.status_code == 409


def _final_states():
    return [
        ServiceRequestStatus.WORKER_COMPLETED,
        ServiceRequestStatus.USER_CONFIRMED,
        ServiceRequestStatus.PAYMENT_PENDING,
        ServiceRequestStatus.PAID,
        ServiceRequestStatus.COMPLETED,
    ]


def test_final_state_requests_do_not_return_candidates(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header,
):
    for status in _final_states():
        _, _, _, service_request, admin = _setup_request(
            make_federation, make_association, make_account, make_user_profile,
            make_service, make_service_request, status=status,
        )
        response = client.get(_url(service_request.id), headers=auth_header(admin))
        assert response.status_code == 409, f"expected 409 for status {status}"


def test_candidate_discovery_does_not_mutate_service_request(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, auth_header, db_session,
):
    _, _, _, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    original_status = service_request.status
    original_updated_at = service_request.updated_at

    client.get(_url(service_request.id), headers=auth_header(admin))

    db_session.refresh(service_request)
    assert service_request.status == original_status
    assert service_request.updated_at == original_updated_at


# =================================================== WORKER ELIGIBILITY ===


def test_active_worker_with_required_skill_appears(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Skilled Active",
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Skilled Active" in names


def test_inactive_worker_excluded(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Inactive Worker", status=WorkerStatus.INACTIVE,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Inactive Worker" not in names


def test_worker_without_required_skill_excluded(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    unskilled_account = make_account(role=AccountRole.WORKER)
    make_worker(
        account_id=unskilled_account.id, association_id=association.id, full_name="Unskilled"
    )
    # Deliberately no `make_worker_skill` call for this worker.

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Unskilled" not in names


def test_worker_from_another_association_excluded(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    federation, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    other_association = make_association(federation_id=federation.id)
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=other_association.id, service_id=service.id, full_name="Elsewhere",
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Elsewhere" not in names


# ======================================================== AVAILABILITY ===


def test_worker_with_pending_response_assignment_same_datetime_excluded(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Busy Worker",
    )
    # A DIFFERENT service request, at the SAME requested_date_time,
    # already has an active (PENDING_RESPONSE) assignment for this worker.
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Busy Worker" not in names


def test_worker_with_accepted_assignment_same_datetime_excluded(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Accepted Elsewhere",
    )
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.ACCEPTED,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Accepted Elsewhere" not in names


def test_worker_with_declined_assignment_still_eligible(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Declined Before",
    )
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.DECLINED,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Declined Before" in names


def test_worker_with_cancelled_by_worker_assignment_still_eligible(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Cancelled Before",
    )
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.CANCELLED_BY_WORKER,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Cancelled Before" in names


def test_worker_with_completed_assignment_still_eligible(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Completed Before",
    )
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME,
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.COMPLETED,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Completed Before" in names


def test_assignment_on_different_datetime_does_not_conflict(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Busy Other Day",
    )
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME + timedelta(days=1),
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.PENDING_RESPONSE,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Busy Other Day" in names


def test_own_request_does_not_create_false_conflict(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header, db_session,
):
    """
    A worker previously offered THIS SAME request (e.g. it declined,
    putting the request back to MATCHING) must not be excluded by its
    own, now-terminal Assignment row on this very request.
    """
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, status=ServiceRequestStatus.MATCHING,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Declined This One",
    )
    make_assignment(
        request_id=service_request.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.DECLINED,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert "Declined This One" in names


# ============================================================= RANKING ===


def test_same_pincode_ranks_before_different_pincode(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Far Away", pincode="999999",
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Same Pincode", pincode="560001",
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert names.index("Same Pincode") < names.index("Far Away")


def test_lower_active_assignment_workload_ranks_first_when_pincode_ties(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _, busy_worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Busy", pincode="560001",
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Free", pincode="560001",
    )
    # Give the "Busy" worker an active assignment on a DIFFERENT datetime
    # so it counts toward workload without creating an availability
    # conflict against the request under test.
    other_user_account = make_account(role=AccountRole.USER)
    other_profile = make_user_profile(account_id=other_user_account.id)
    other_request = make_service_request(
        user_id=other_profile.id,
        service_id=service.id,
        association_id=association.id,
        requested_date_time=REQUEST_DATETIME + timedelta(days=2),
    )
    make_assignment(
        request_id=other_request.id,
        worker_id=busy_worker.id,
        assigned_by=admin.id,
        status=AssignmentStatus.ACCEPTED,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    items = response.json()["items"]
    names = [item["fullName"] for item in items]
    assert names.index("Free") < names.index("Busy")
    busy_item = next(item for item in items if item["fullName"] == "Busy")
    free_item = next(item for item in items if item["fullName"] == "Free")
    assert busy_item["activeAssignmentCount"] == 1
    assert free_item["activeAssignmentCount"] == 0


def test_higher_rating_ranks_first_when_previous_factors_tie(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Lower Rated", pincode="560001", rating=Decimal("2.00"),
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Higher Rated", pincode="560001", rating=Decimal("4.75"),
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    names = [item["fullName"] for item in response.json()["items"]]
    assert names.index("Higher Rated") < names.index("Lower Rated")


def test_worker_id_is_deterministic_final_tiebreaker(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _, worker_a = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Twin A", pincode="560001", rating=Decimal("4.00"),
    )
    _, worker_b = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Twin B", pincode="560001", rating=Decimal("4.00"),
    )
    expected_first, expected_second = sorted([worker_a.id, worker_b.id], key=str)

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    ids = [item["workerId"] for item in response.json()["items"]]
    assert ids == [str(expected_first), str(expected_second)]


def test_total_jobs_completed_does_not_affect_ranking(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    """
    Same pincode, same active-assignment count (0), same rating -- only
    `total_jobs_completed` differs. Ordering must fall through to the
    Worker.id tiebreaker exactly as the "no other factors" case would,
    proving `total_jobs_completed` played no role.
    """
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _, worker_many_jobs = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Many Jobs", pincode="560001", rating=Decimal("4.00"),
        total_jobs_completed=500,
    )
    _, worker_few_jobs = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Few Jobs", pincode="560001", rating=Decimal("4.00"),
        total_jobs_completed=0,
    )
    expected_first, expected_second = sorted(
        [worker_many_jobs.id, worker_few_jobs.id], key=str
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    ids = [item["workerId"] for item in response.json()["items"]]
    assert ids == [str(expected_first), str(expected_second)]


# ============================================================= RESPONSE ===


def test_response_uses_camel_case_and_all_required_fields(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Field Check", pincode="560001", rating=Decimal("3.50"),
        total_jobs_completed=9,
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "page", "pageSize", "total"}
    item = body["items"][0]
    assert set(item.keys()) == {
        "workerId",
        "workerCode",
        "fullName",
        "phoneNumber",
        "address",
        "pincode",
        "rating",
        "totalJobsCompleted",
        "activeAssignmentCount",
        "samePincode",
    }
    assert item["samePincode"] is True
    assert item["activeAssignmentCount"] == 0
    assert item["totalJobsCompleted"] == 9


def test_no_password_hash_or_auth_secrets_exposed(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    account = make_account(role=AccountRole.WORKER, password="supersecret123")
    worker = make_worker(account_id=account.id, association_id=association.id)
    make_worker_skill(worker_id=worker.id, service_id=service.id)

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert "password" not in response.text.lower()
    assert "supersecret123" not in response.text


def test_active_assignment_count_is_correct(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill,
    make_assignment, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Two Active",
    )
    for _ in range(2):
        other_user_account = make_account(role=AccountRole.USER)
        other_profile = make_user_profile(account_id=other_user_account.id)
        other_request = make_service_request(
            user_id=other_profile.id,
            service_id=service.id,
            association_id=association.id,
            requested_date_time=REQUEST_DATETIME + timedelta(days=3),
        )
        make_assignment(
            request_id=other_request.id,
            worker_id=worker.id,
            assigned_by=admin.id,
            status=AssignmentStatus.ACCEPTED,
        )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    item = next(i for i in response.json()["items"] if i["fullName"] == "Two Active")
    assert item["activeAssignmentCount"] == 2


def test_same_pincode_field_is_correct_for_different_pincode(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id,
        full_name="Different Pincode", pincode="110001",
    )

    response = client.get(_url(service_request.id), headers=auth_header(admin))
    item = next(i for i in response.json()["items"] if i["fullName"] == "Different Pincode")
    assert item["samePincode"] is False


# ============================================================ PAGINATION ===


def test_pagination_page_and_page_size_work(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    for i in range(3):
        _make_eligible_worker(
            make_account, make_worker, make_worker_skill,
            association_id=association.id, service_id=service.id, full_name=f"Worker {i}",
        )

    response = client.get(
        _url(service_request.id),
        params={"page": 1, "page_size": 2},
        headers=auth_header(admin),
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["pageSize"] == 2


def test_pagination_ordering_is_deterministic_across_pages(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
):
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request, pincode="560001",
    )
    created_ids = []
    for i in range(3):
        _, worker = _make_eligible_worker(
            make_account, make_worker, make_worker_skill,
            association_id=association.id, service_id=service.id,
            full_name=f"Worker {i}", pincode="560001", rating=Decimal("3.00"),
        )
        created_ids.append(worker.id)
    expected_order = sorted(str(i) for i in created_ids)

    page1 = client.get(
        _url(service_request.id), params={"page": 1, "page_size": 2}, headers=auth_header(admin)
    ).json()
    page2 = client.get(
        _url(service_request.id), params={"page": 2, "page_size": 2}, headers=auth_header(admin)
    ).json()

    all_ids = [item["workerId"] for item in page1["items"]] + [
        item["workerId"] for item in page2["items"]
    ]
    assert all_ids == expected_order


# ============================================================ REGRESSION ===


def test_5e_e_assignment_endpoint_unaffected_by_candidate_discovery(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, make_service_request, make_worker, make_worker_skill, auth_header,
    db_session,
):
    """
    Calling the new read-only candidate endpoint must have no effect on
    the existing manual-assignment endpoint's own behavior: it still
    requires an explicit worker_id, still requires PENDING/MATCHING, and
    still results in exactly one Assignment.
    """
    _, association, service, service_request, admin = _setup_request(
        make_federation, make_association, make_account, make_user_profile,
        make_service, make_service_request,
    )
    _, worker = _make_eligible_worker(
        make_account, make_worker, make_worker_skill,
        association_id=association.id, service_id=service.id, full_name="Chosen One",
    )

    # Call candidate discovery first -- must not mutate anything.
    candidates_response = client.get(_url(service_request.id), headers=auth_header(admin))
    assert candidates_response.status_code == 200
    assert len(candidates_response.json()["items"]) == 1

    # The admin must still explicitly choose and POST to assign.
    assign_response = client.post(
        ASSIGNMENTS_URL.format(request_id=service_request.id),
        json={"workerId": str(worker.id)},
        headers=auth_header(admin),
    )
    assert assign_response.status_code == 201
    assert assign_response.json()["workerId"] == str(worker.id)
    assert assign_response.json()["status"] == AssignmentStatus.PENDING_RESPONSE.value

    db_session.refresh(service_request)
    assert service_request.status == ServiceRequestStatus.ASSIGNED
