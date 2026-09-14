"""Интеграционные тесты /api/reminders: CRUD, фильтры, /send, изоляция по организации."""

from tests.conftest import register_and_login


def test_create_reminder(client, auth_headers):
    resp = client.post(
        "/api/reminders",
        json={"type": "rto_deadline", "target_date": "2026-10-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "rto_deadline"
    assert data["target_date"] == "2026-10-01"
    assert data["sent"] is False
    assert data["telegram_message_id"] is None


def test_reminders_require_auth(client):
    resp = client.get("/api/reminders")
    assert resp.status_code == 401


def test_list_reminders_for_own_organization(client, auth_headers):
    client.post(
        "/api/reminders",
        json={"type": "etrn_deadline", "target_date": "2026-10-05"},
        headers=auth_headers,
    )
    resp = client.get("/api/reminders", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "etrn_deadline"


def test_list_reminders_filtered_by_type_and_sent(client, auth_headers):
    client.post(
        "/api/reminders",
        json={"type": "rto_deadline", "target_date": "2026-10-01"},
        headers=auth_headers,
    )
    resp = client.post(
        "/api/reminders",
        json={"type": "vehicle_inspection", "target_date": "2026-11-01"},
        headers=auth_headers,
    )
    inspection_id = resp.json()["id"]
    client.post(f"/api/reminders/{inspection_id}/send", headers=auth_headers)

    resp = client.get("/api/reminders", params={"type": "rto_deadline"}, headers=auth_headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["type"] == "rto_deadline"

    resp = client.get("/api/reminders", params={"sent": "true"}, headers=auth_headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == inspection_id

    resp = client.get("/api/reminders", params={"sent": "false"}, headers=auth_headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["type"] == "rto_deadline"


def test_send_reminder_marks_sent_via_console_sender(client, auth_headers, caplog):
    resp = client.post(
        "/api/reminders",
        json={"type": "custom", "target_date": "2026-12-01"},
        headers=auth_headers,
    )
    reminder_id = resp.json()["id"]

    with caplog.at_level("INFO", logger="app.reminders"):
        resp = client.post(f"/api/reminders/{reminder_id}/send", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] is True
    assert data["telegram_message_id"] is None
    assert any("Reminder mock" in message for message in caplog.messages)


def test_send_unknown_reminder_is_404(client, auth_headers):
    resp = client.post(
        "/api/reminders/00000000-0000-0000-0000-000000000000/send", headers=auth_headers
    )
    assert resp.status_code == 404


def test_reminders_do_not_leak_other_organizations(client, fake_sms, auth_headers):
    client.post(
        "/api/reminders",
        json={"type": "rto_deadline", "target_date": "2026-10-01"},
        headers=auth_headers,
    )

    other_tokens = register_and_login(client, fake_sms, phone="+79990000005")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.get("/api/reminders", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_send_reminder_for_foreign_organization_is_404(client, fake_sms, auth_headers):
    resp = client.post(
        "/api/reminders",
        json={"type": "rto_deadline", "target_date": "2026-10-01"},
        headers=auth_headers,
    )
    reminder_id = resp.json()["id"]

    other_tokens = register_and_login(client, fake_sms, phone="+79990000006")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.post(f"/api/reminders/{reminder_id}/send", headers=other_headers)
    assert resp.status_code == 404
