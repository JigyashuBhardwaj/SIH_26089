"""
Tests for the Phase 5E-B read-only service catalogue routes:
`GET /services` and `GET /services/{service_id}`.
"""

import uuid


def test_list_services_returns_200(client, make_account, auth_header, make_service):
    make_service()
    account = make_account()

    response = client.get("/services", headers=auth_header(account))

    assert response.status_code == 200


def test_list_services_returns_only_active_services(
    client, make_account, auth_header, make_service
):
    active = make_service(name="Active Plumbing")
    make_service(name="Retired Service", is_active=False)
    account = make_account()

    response = client.get("/services", headers=auth_header(account))

    body = response.json()
    names = [item["name"] for item in body["items"]]
    assert "Active Plumbing" in names
    assert "Retired Service" not in names
    assert all(item["isActive"] is True for item in body["items"])
    assert str(active.id) in [item["id"] for item in body["items"]]


def test_list_services_response_shape(client, make_account, auth_header, make_service):
    make_service()
    account = make_account()

    response = client.get("/services", headers=auth_header(account))

    body = response.json()
    assert set(body.keys()) == {"items", "page", "pageSize", "total"}
    assert body["page"] == 1
    assert body["pageSize"] == 20
    item = body["items"][0]
    assert set(item.keys()) == {"id", "name", "category", "isActive"}


def test_list_services_pagination_bounds_and_ordering(
    client, make_account, auth_header, make_service
):
    make_service(name="Bravo")
    make_service(name="Alpha")
    make_service(name="Charlie")
    account = make_account()

    page_1 = client.get(
        "/services", headers=auth_header(account), params={"page": 1, "page_size": 2}
    )
    page_2 = client.get(
        "/services", headers=auth_header(account), params={"page": 2, "page_size": 2}
    )

    assert page_1.status_code == 200
    assert page_2.status_code == 200
    page_1_body = page_1.json()
    page_2_body = page_2.json()

    assert page_1_body["pageSize"] == 2
    assert len(page_1_body["items"]) == 2
    assert len(page_2_body["items"]) >= 1
    # Deterministic ordering: name ascending.
    names_in_order = [item["name"] for item in page_1_body["items"]] + [
        item["name"] for item in page_2_body["items"]
    ]
    assert names_in_order == sorted(names_in_order)


def test_list_services_rejects_page_size_over_maximum(client, make_account, auth_header):
    account = make_account()

    response = client.get(
        "/services", headers=auth_header(account), params={"page_size": 1000}
    )

    assert response.status_code == 422


def test_list_services_unauthenticated_returns_401(client):
    response = client.get("/services")

    assert response.status_code == 401


def test_get_service_active_returns_200(client, make_account, auth_header, make_service):
    service = make_service()
    account = make_account()

    response = client.get(f"/services/{service.id}", headers=auth_header(account))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(service.id)
    assert body["isActive"] is True


def test_get_service_inactive_returns_404(client, make_account, auth_header, make_service):
    service = make_service(is_active=False)
    account = make_account()

    response = client.get(f"/services/{service.id}", headers=auth_header(account))

    assert response.status_code == 404


def test_get_service_nonexistent_returns_404(client, make_account, auth_header):
    account = make_account()

    response = client.get(f"/services/{uuid.uuid4()}", headers=auth_header(account))

    assert response.status_code == 404


def test_get_service_malformed_uuid_returns_422(client, make_account, auth_header):
    account = make_account()

    response = client.get("/services/not-a-uuid", headers=auth_header(account))

    assert response.status_code == 422


def test_get_service_unauthenticated_returns_401(client, make_service):
    service = make_service()

    response = client.get(f"/services/{service.id}")

    assert response.status_code == 401
