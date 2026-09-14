"""Интеграционные тесты /api/vehicles, включая PATCH."""

from tests.conftest import register_and_login


def create_vehicle(client, auth_headers, plate_number="А000АА00"):
    resp = client.post(
        "/api/vehicles",
        json={"plate_number": plate_number, "brand_model": "КамАЗ"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_patch_vehicle_updates_next_inspection_date(client, auth_headers):
    vehicle = create_vehicle(client, auth_headers)
    assert vehicle["next_inspection_date"] is None

    resp = client.patch(
        f"/api/vehicles/{vehicle['id']}",
        json={"next_inspection_date": "2026-10-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_inspection_date"] == "2026-10-01"
    # Остальные поля не тронуты.
    assert data["plate_number"] == vehicle["plate_number"]
    assert data["brand_model"] == "КамАЗ"


def test_patch_vehicle_partial_update_does_not_touch_other_fields(client, auth_headers):
    vehicle = create_vehicle(client, auth_headers)

    resp = client.patch(
        f"/api/vehicles/{vehicle['id']}",
        json={"brand_model": "Volvo FH"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand_model"] == "Volvo FH"
    assert data["plate_number"] == vehicle["plate_number"]
    assert data["next_inspection_date"] is None


def test_patch_vehicle_unknown_is_404(client, auth_headers):
    resp = client.patch(
        "/api/vehicles/00000000-0000-0000-0000-000000000000",
        json={"brand_model": "Volvo"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_patch_vehicle_for_foreign_organization_is_404(client, fake_sms, auth_headers):
    vehicle = create_vehicle(client, auth_headers)

    other_tokens = register_and_login(client, fake_sms, phone="+79990000010")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.patch(
        f"/api/vehicles/{vehicle['id']}",
        json={"brand_model": "Чужой"},
        headers=other_headers,
    )
    assert resp.status_code == 404
