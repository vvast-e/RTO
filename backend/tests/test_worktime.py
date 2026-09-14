"""Интеграционные тесты CRUD /api/worktime."""

from tests.conftest import register_and_login


def create_driver(client, auth_headers, full_name="Иван Петров"):
    resp = client.post("/api/drivers", json={"full_name": full_name}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def test_create_and_get_worktime_entry(client, auth_headers):
    driver = create_driver(client, auth_headers)
    payload = {
        "driver_id": driver["id"],
        "entry_type": "driving",
        "start_time": "2026-09-14T06:00:00Z",
        "end_time": "2026-09-14T10:00:00Z",
    }
    resp = client.post("/api/worktime", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    entry = resp.json()
    assert entry["driver_id"] == driver["id"]
    assert entry["entry_type"] == "driving"

    resp = client.get(f"/api/worktime/{entry['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == entry["id"]


def test_list_worktime_entries_filtered_by_driver(client, auth_headers):
    driver1 = create_driver(client, auth_headers, "Водитель Один")
    driver2 = create_driver(client, auth_headers, "Водитель Два")
    for driver in (driver1, driver2):
        client.post(
            "/api/worktime",
            json={
                "driver_id": driver["id"],
                "entry_type": "driving",
                "start_time": "2026-09-14T06:00:00Z",
                "end_time": "2026-09-14T10:00:00Z",
            },
            headers=auth_headers,
        )

    resp = client.get("/api/worktime", params={"driver_id": driver1["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["driver_id"] == driver1["id"]


def test_create_worktime_entry_for_unknown_driver_is_404(client, auth_headers):
    resp = client.post(
        "/api/worktime",
        json={
            "driver_id": "00000000-0000-0000-0000-000000000000",
            "entry_type": "driving",
            "start_time": "2026-09-14T06:00:00Z",
            "end_time": "2026-09-14T10:00:00Z",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_create_worktime_entry_for_foreign_driver_is_404(client, fake_sms, auth_headers):
    driver = create_driver(client, auth_headers)

    other_tokens = register_and_login(client, fake_sms, phone="+79990000002")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.post(
        "/api/worktime",
        json={
            "driver_id": driver["id"],
            "entry_type": "driving",
            "start_time": "2026-09-14T06:00:00Z",
            "end_time": "2026-09-14T10:00:00Z",
        },
        headers=other_headers,
    )
    assert resp.status_code == 404


def test_worktime_requires_auth(client):
    resp = client.get("/api/worktime")
    assert resp.status_code == 401
