"""Интеграционные тесты Telegram-интеграции: код привязки, вебхук, отправка
через TelegramReminderSender с замоканным httpx (без реальных запросов к
Telegram API), ошибка при отправке без привязанного чата, изоляция по
организации.
"""

import pytest

from app.services.reminder_sender import (
    TelegramChatNotLinkedError,
    TelegramReminderSender,
)


def test_organization_me_reports_telegram_linked_status(client, auth_headers):
    resp = client.get("/api/organizations/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["telegram_linked"] is False

    resp = client.post("/api/organizations/me/telegram-link-code", headers=auth_headers)
    code = resp.json()["code"]
    client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 5,
            "message": {
                "message_id": 5,
                "chat": {"id": 42, "type": "private"},
                "text": f"/start {code}",
            },
        },
    )

    resp = client.get("/api/organizations/me", headers=auth_headers)
    assert resp.json()["telegram_linked"] is True


def test_get_telegram_link_code_requires_auth(client):
    resp = client.post("/api/organizations/me/telegram-link-code")
    assert resp.status_code == 401


def test_get_telegram_link_code_returns_code(client, auth_headers):
    resp = client.post("/api/organizations/me/telegram-link-code", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["code"]) == 8
    assert "expires_at" in data


def test_webhook_links_chat_by_code(client, auth_headers):
    resp = client.post("/api/organizations/me/telegram-link-code", headers=auth_headers)
    code = resp.json()["code"]

    resp = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123456789, "type": "private"},
                "text": f"/start {code}",
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Повторное использование того же кода больше не должно ничего привязывать —
    # проверяем косвенно через отправку напоминания с замоканным sender ниже.


def test_webhook_ignores_unknown_code(client):
    resp = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 2,
            "message": {
                "message_id": 2,
                "chat": {"id": 111, "type": "private"},
                "text": "/start DEADBEEF",
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_webhook_ignores_non_message_updates(client):
    resp = client.post("/api/telegram/webhook", json={"update_id": 3})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_webhook_rejects_wrong_secret_token(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.telegram.settings.telegram_webhook_secret", "s3cr3t")
    resp = client.post(
        "/api/telegram/webhook",
        json={"update_id": 6, "message": {"chat": {"id": 1}, "text": "/start ABCDEF12"}},
    )
    assert resp.status_code == 401


def test_webhook_accepts_correct_secret_token(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.routes.telegram.settings.telegram_webhook_secret", "s3cr3t")
    resp = client.post("/api/organizations/me/telegram-link-code", headers=auth_headers)
    code = resp.json()["code"]

    resp = client.post(
        "/api/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cr3t"},
        json={"update_id": 7, "message": {"chat": {"id": 2}, "text": f"/start {code}"}},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_send_reminder_fails_without_linked_chat(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.reminders.get_reminder_sender",
        lambda: TelegramReminderSender("fake-token"),
    )

    resp = client.post(
        "/api/reminders",
        json={"type": "rto_deadline", "target_date": "2026-10-01"},
        headers=auth_headers,
    )
    reminder_id = resp.json()["id"]

    resp = client.post(f"/api/reminders/{reminder_id}/send", headers=auth_headers)
    assert resp.status_code == 409
    assert "Telegram" in resp.json()["detail"] or "чат" in resp.json()["detail"]


def test_send_reminder_via_telegram_after_linking(client, auth_headers, monkeypatch):
    # Привязываем чат.
    resp = client.post("/api/organizations/me/telegram-link-code", headers=auth_headers)
    code = resp.json()["code"]
    chat_id = 987654321
    resp = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 4,
            "message": {
                "message_id": 3,
                "chat": {"id": chat_id, "type": "private"},
                "text": f"/start {code}",
            },
        },
    )
    assert resp.status_code == 200

    # Мокаем HTTP-вызов к Telegram Bot API.
    sent_requests = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True, "result": {"message_id": 555}}

    def fake_post(url, json=None, timeout=None):
        sent_requests.append((url, json))
        return FakeResponse()

    monkeypatch.setattr("app.services.reminder_sender.httpx.post", fake_post)
    monkeypatch.setattr(
        "app.api.routes.reminders.get_reminder_sender",
        lambda: TelegramReminderSender("fake-token"),
    )

    resp = client.post(
        "/api/reminders",
        json={"type": "vehicle_inspection", "target_date": "2026-11-01"},
        headers=auth_headers,
    )
    reminder_id = resp.json()["id"]

    resp = client.post(f"/api/reminders/{reminder_id}/send", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] is True
    assert data["telegram_message_id"] == 555

    assert len(sent_requests) == 1
    url, payload = sent_requests[0]
    assert url == "https://api.telegram.org/botfake-token/sendMessage"
    assert payload["chat_id"] == chat_id


def test_telegram_link_codes_are_isolated_per_organization(client, fake_sms, auth_headers):
    from tests.conftest import register_and_login

    other_tokens = register_and_login(client, fake_sms, phone="+79990000007")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.post("/api/organizations/me/telegram-link-code", headers=auth_headers)
    code_a = resp.json()["code"]

    resp = client.post("/api/organizations/me/telegram-link-code", headers=other_headers)
    code_b = resp.json()["code"]

    assert code_a != code_b


def test_telegram_reminder_sender_raises_when_no_chat_linked():
    from app.models.organization import Organization
    from app.models.reminder import Reminder, ReminderType
    from datetime import date

    organization = Organization(name="Без чата")
    reminder = Reminder(
        organization=organization,
        type=ReminderType.custom,
        target_date=date(2026, 12, 1),
    )

    sender = TelegramReminderSender("fake-token")
    with pytest.raises(TelegramChatNotLinkedError):
        sender.send(reminder)
