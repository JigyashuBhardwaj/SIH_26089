"""
Tests for the Phase 5E-C `ServiceRequest` routes:
`POST /requests`, `GET /requests`, `GET /requests/{request_id}`.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update as sa_update

from app.models.enums import AccountRole, ServiceRequestStatus
from app.models.service_request import ServiceRequest

VALID_LEAD = timedelta(hours=5)
TOO_SOON_LEAD = timedelta(hours=1)


def _valid_payload(*, service_id, association_id, lead=VALID_LEAD) -> dict:
    requested = datetime.now(timezone.utc) + lead
    return {
        "serviceId": str(service_id),
        "associationId": str(association_id),
        "requestedDateTime": requested.isoformat(),
        "address": "12 MG Road",
        "pincode": "560001",
    }


def _make_user(make_account, make_user_profile, *, full_name="Test User"):
    account = make_account(role=AccountRole.USER)
    profile = make_user_profile(account_id=account.id, full_name=full_name)
    return account, profile


# --- Creation -----------------------------------------------------------


def test_valid_user_can_create_request_returns_201(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    assert response.status_code == 201


def test_newly_created_request_status_is_pending(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    assert response.json()["status"] == ServiceRequestStatus.PENDING.value


def test_request_code_is_database_generated(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    body = response.json()
    assert body["requestCode"]
    assert body["requestCode"].startswith("REQ-")


def test_created_request_belongs_to_authenticated_users_profile(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header, db_session,
):
    account, profile = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    from app.models.service_request import ServiceRequest

    created_id = uuid.UUID(response.json()["id"])
    row = db_session.get(ServiceRequest, created_id)
    assert row.user_id == profile.id


def test_create_response_has_exact_expected_shape(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    body = response.json()
    assert set(body.keys()) == {
        "id",
        "requestCode",
        "serviceId",
        "associationId",
        "requestedDateTime",
        "address",
        "pincode",
        "status",
        "createdAt",
        "updatedAt",
        # Phase 6E-A: always present, always null on a freshly-created
        # (PENDING, no Assignment yet) request -- see the assertions in
        # test_create_response_does_not_expose_assignment_info below.
        "assignedWorkerId",
        "assignedWorkerName",
        "assignedWorkerPhone",
    }


def test_create_response_does_not_expose_user_id(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    body = response.json()
    assert "userId" not in body
    assert "user_id" not in body


def test_create_response_does_not_expose_worker_id(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    body = response.json()
    assert "workerId" not in body
    assert "worker_id" not in body


def test_create_response_does_not_expose_assignment_info(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    body = response.json()
    assert not any("assignment" in key.lower() for key in body.keys())


# --- Service validation ---------------------------------------------------


def test_create_with_inactive_service_returns_404(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service(is_active=False)

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    assert response.status_code == 404


def test_create_with_nonexistent_service_returns_404(
    client, make_account, make_user_profile, make_federation, make_association,
    auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=uuid.uuid4(), association_id=association.id),
    )

    assert response.status_code == 404


# --- Association validation -----------------------------------------------


def test_create_with_nonexistent_association_returns_404(
    client, make_account, make_user_profile, make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=uuid.uuid4()),
    )

    assert response.status_code == 404


# --- Datetime validation ----------------------------------------------------


def test_create_with_requested_time_less_than_4_hours_rejected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(
            service_id=service.id, association_id=association.id, lead=TOO_SOON_LEAD
        ),
    )

    assert response.status_code == 422


def test_create_with_requested_time_at_least_4_hours_accepted(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(
            service_id=service.id, association_id=association.id, lead=VALID_LEAD
        ),
    )

    assert response.status_code == 201


def test_create_with_naive_datetime_rejected(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    payload = _valid_payload(service_id=service.id, association_id=association.id)
    naive = (datetime.now() + VALID_LEAD).replace(tzinfo=None)
    payload["requestedDateTime"] = naive.isoformat()  # no offset/'Z'

    response = client.post("/requests", headers=auth_header(account), json=payload)

    assert response.status_code == 422


def test_create_with_missing_required_field_returns_422(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    payload = _valid_payload(service_id=service.id, association_id=association.id)
    del payload["address"]

    response = client.post("/requests", headers=auth_header(account), json=payload)

    assert response.status_code == 422


def test_create_with_unexpected_user_id_field_returns_422(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    """
    The server owns `userId` -- a client attempting to supply it must be
    rejected outright (`extra="forbid"`), not silently ignored.
    """
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    payload = _valid_payload(service_id=service.id, association_id=association.id)
    payload["userId"] = str(uuid.uuid4())

    response = client.post("/requests", headers=auth_header(account), json=payload)

    assert response.status_code == 422


def test_create_with_unexpected_status_field_returns_422(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    """The server owns `status` -- a client attempting to set it must be rejected."""
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    payload = _valid_payload(service_id=service.id, association_id=association.id)
    payload["status"] = ServiceRequestStatus.COMPLETED.value

    response = client.post("/requests", headers=auth_header(account), json=payload)

    assert response.status_code == 422


# --- Profile ----------------------------------------------------------------


def test_create_without_user_profile_returns_404(
    client, make_account, make_federation, make_association, make_service, auth_header,
):
    account = make_account(role=AccountRole.USER)  # no UserProfile created
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    response = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    assert response.status_code == 404


# --- Listing ------------------------------------------------------------


def test_user_can_list_own_requests_returns_200(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()
    client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    response = client.get("/requests", headers=auth_header(account))

    assert response.status_code == 200


def test_list_contains_only_authenticated_users_requests(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account_a, _ = _make_user(make_account, make_user_profile, full_name="User A")
    account_b, _ = _make_user(make_account, make_user_profile, full_name="User B")
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    create_response = client.post(
        "/requests",
        headers=auth_header(account_a),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )
    own_request_id = create_response.json()["id"]

    client.post(
        "/requests",
        headers=auth_header(account_b),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    response = client.get("/requests", headers=auth_header(account_a))

    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert own_request_id in ids
    assert len(ids) == 1


def test_other_users_requests_never_returned(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account_a, _ = _make_user(make_account, make_user_profile, full_name="User A")
    account_b, _ = _make_user(make_account, make_user_profile, full_name="User B")
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    client.post(
        "/requests",
        headers=auth_header(account_b),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    response = client.get("/requests", headers=auth_header(account_a))

    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_list_pagination_works(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()
    for _ in range(3):
        client.post(
            "/requests",
            headers=auth_header(account),
            json=_valid_payload(service_id=service.id, association_id=association.id),
        )

    page_1 = client.get(
        "/requests", headers=auth_header(account), params={"page": 1, "page_size": 2}
    )
    page_2 = client.get(
        "/requests", headers=auth_header(account), params={"page": 2, "page_size": 2}
    )

    assert len(page_1.json()["items"]) == 2
    assert len(page_2.json()["items"]) == 1
    assert page_1.json()["total"] == 3


def test_list_ordering_is_newest_first(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header, db_session,
):
    """
    Within a single test transaction, PostgreSQL's `now()` (backing
    `created_at`'s server default) returns the *transaction* start time,
    so two requests created back-to-back in the same test can end up with
    an identical `created_at` -- that's a property of the shared test
    transaction, not of the route. To actually exercise the `created_at
    DESC` ordering (rather than relying on incidental wall-clock timing),
    force two distinct timestamps directly and confirm the response
    honors them.
    """
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()

    older = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    ).json()
    newer = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    ).json()

    base = datetime.now(timezone.utc)
    db_session.execute(
        sa_update(ServiceRequest)
        .where(ServiceRequest.id == uuid.UUID(older["id"]))
        .values(created_at=base - timedelta(minutes=10))
    )
    db_session.execute(
        sa_update(ServiceRequest)
        .where(ServiceRequest.id == uuid.UUID(newer["id"]))
        .values(created_at=base)
    )
    db_session.flush()

    response = client.get("/requests", headers=auth_header(account))

    ids_in_order = [item["id"] for item in response.json()["items"]]
    assert ids_in_order == [newer["id"], older["id"]]


def test_list_ordering_is_deterministic_when_timestamps_tie(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    """
    Two requests created in the same transaction can share an identical
    `created_at` (see the note above). The route must still return a
    stable, repeatable order rather than an arbitrary one -- verified
    here by issuing the same query twice and checking the order matches.
    """
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()
    client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )
    client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    )

    first_call = client.get("/requests", headers=auth_header(account))
    second_call = client.get("/requests", headers=auth_header(account))

    first_ids = [item["id"] for item in first_call.json()["items"]]
    second_ids = [item["id"] for item in second_call.json()["items"]]
    assert first_ids == second_ids


def test_list_unauthenticated_returns_401(client):
    response = client.get("/requests")

    assert response.status_code == 401


# --- Single request retrieval ------------------------------------------


def test_user_can_retrieve_own_request_returns_200(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account, _ = _make_user(make_account, make_user_profile)
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()
    created = client.post(
        "/requests",
        headers=auth_header(account),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    ).json()

    response = client.get(f"/requests/{created['id']}", headers=auth_header(account))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_user_cannot_retrieve_another_users_request_returns_404(
    client, make_account, make_user_profile, make_federation, make_association,
    make_service, auth_header,
):
    account_a, _ = _make_user(make_account, make_user_profile, full_name="User A")
    account_b, _ = _make_user(make_account, make_user_profile, full_name="User B")
    federation = make_federation()
    association = make_association(federation_id=federation.id)
    service = make_service()
    created = client.post(
        "/requests",
        headers=auth_header(account_b),
        json=_valid_payload(service_id=service.id, association_id=association.id),
    ).json()

    response = client.get(f"/requests/{created['id']}", headers=auth_header(account_a))

    assert response.status_code == 404


def test_nonexistent_request_returns_404(client, make_account, make_user_profile, auth_header):
    account, _ = _make_user(make_account, make_user_profile)

    response = client.get(f"/requests/{uuid.uuid4()}", headers=auth_header(account))

    assert response.status_code == 404


def test_malformed_request_uuid_returns_422(client, make_account, make_user_profile, auth_header):
    account, _ = _make_user(make_account, make_user_profile)

    response = client.get("/requests/not-a-uuid", headers=auth_header(account))

    assert response.status_code == 422


# --- Authorization --------------------------------------------------------


def test_unauthenticated_post_returns_401(client):
    response = client.post(
        "/requests",
        json=_valid_payload(service_id=uuid.uuid4(), association_id=uuid.uuid4()),
    )

    assert response.status_code == 401


def test_unauthenticated_get_returns_401(client):
    response = client.get(f"/requests/{uuid.uuid4()}")

    assert response.status_code == 401


def test_worker_role_receives_403(client, make_account, auth_header):
    account = make_account(role=AccountRole.WORKER)

    response = client.get("/requests", headers=auth_header(account))

    assert response.status_code == 403


def test_association_admin_role_receives_403(client, make_account, auth_header):
    account = make_account(role=AccountRole.ASSOCIATION_ADMIN)

    response = client.get("/requests", headers=auth_header(account))

    assert response.status_code == 403


def test_federation_admin_role_receives_403(client, make_account, auth_header):
    account = make_account(role=AccountRole.FEDERATION_ADMIN)

    response = client.get("/requests", headers=auth_header(account))

    assert response.status_code == 403
