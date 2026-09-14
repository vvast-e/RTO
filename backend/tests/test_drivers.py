"""Интеграционные тесты /api/drivers, включая PATCH."""

from tests.conftest import register_and_login


def create_driver(client, auth_headers, full_name="Иван Петров"):
    resp = client.post("/api/drivers", json={"full_name": full_name}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def test_patch_driver_updates_license_expiry_date(client, auth_headers):
    driver = create_driver(client, auth_headers)
    assert driver["license_expiry_date"] is None

    resp = client.patch(
        f"/api/drivers/{driver['id']}",
        json={"license_expiry_date": "2026-11-15"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["license_expiry_date"] == "2026-11-15"
    assert data["full_name"] == driver["full_name"]


def test_patch_driver_partial_update_does_not_touch_other_fields(client, auth_headers):
    driver = create_driver(client, auth_headers)

    resp = client.patch(
        f"/api/drivers/{driver['id']}",
        json={"phone": "+79990001122"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == "+79990001122"
    assert data["full_name"] == driver["full_name"]
    assert data["license_expiry_date"] is None


def test_patch_driver_unknown_is_404(client, auth_headers):
    resp = client.patch(
        "/api/drivers/00000000-0000-0000-0000-000000000000",
        json={"full_name": "Кто-то"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_patch_driver_for_foreign_organization_is_404(client, fake_sms, auth_headers):
    driver = create_driver(client, auth_headers)

    other_tokens = register_and_login(client, fake_sms, phone="+79990000011")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.patch(
        f"/api/drivers/{driver['id']}",
        json={"full_name": "Чужой"},
        headers=other_headers,
    )
    assert resp.status_code == 404
