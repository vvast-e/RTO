"""Синхронный вызов Celery-таска автоматической рассылки напоминаний (без
брокера — через прямой вызов .run(), как и в test_rto_tasks.py)."""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.organization import Organization
from app.models.reminder import Reminder, ReminderType
from app.services.reminder_sender import TelegramChatNotLinkedError
from app.tasks.reminder_tasks import send_due_reminders_task

TODAY = date(2026, 9, 14)


def _make_org(db, name: str, telegram_chat_id: int | None = None) -> Organization:
    org = Organization(name=name, telegram_chat_id=telegram_chat_id)
    db.add(org)
    db.flush()
    return org


@pytest.fixture()
def session_local(db_engine, monkeypatch):
    session_local = sessionmaker(bind=db_engine)
    monkeypatch.setattr("app.tasks.reminder_tasks.SessionLocal", session_local)
    return session_local


class _RecordingSender:
    """Тестовый ReminderSender — записывает отправленные напоминания, не
    делает реальных запросов. Организация без telegram_chat_id считается
    непривязанной (как настоящий TelegramReminderSender)."""

    def __init__(self):
        self.sent: list[Reminder] = []

    def send(self, reminder: Reminder) -> int | None:
        if reminder.organization.telegram_chat_id is None:
            raise TelegramChatNotLinkedError("чат не привязан")
        self.sent.append(reminder)
        return 111


def _patch_sender(monkeypatch, sender):
    monkeypatch.setattr("app.tasks.reminder_tasks.get_reminder_sender", lambda: sender)


def test_sends_only_overdue_unsent_reminders(session_local, monkeypatch):
    sender = _RecordingSender()
    _patch_sender(monkeypatch, sender)

    db = session_local()
    try:
        org = _make_org(db, "Организация", telegram_chat_id=1)
        overdue = Reminder(
            organization_id=org.id, type=ReminderType.rto_deadline, target_date=TODAY - timedelta(days=1)
        )
        due_today = Reminder(
            organization_id=org.id, type=ReminderType.rto_deadline, target_date=TODAY
        )
        future = Reminder(
            organization_id=org.id, type=ReminderType.rto_deadline, target_date=TODAY + timedelta(days=1)
        )
        db.add_all([overdue, due_today, future])
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("app.tasks.reminder_tasks.date", type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}))

    sent_count = send_due_reminders_task.run()
    assert sent_count == 2

    db = session_local()
    try:
        reminders = {r.target_date: r.sent for r in db.query(Reminder).all()}
        assert reminders[TODAY - timedelta(days=1)] is True
        assert reminders[TODAY] is True
        assert reminders[TODAY + timedelta(days=1)] is False
    finally:
        db.close()


def test_does_not_touch_already_sent_reminders(session_local, monkeypatch):
    sender = _RecordingSender()
    _patch_sender(monkeypatch, sender)
    monkeypatch.setattr("app.tasks.reminder_tasks.date", type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}))

    db = session_local()
    try:
        org = _make_org(db, "Организация", telegram_chat_id=1)
        already_sent = Reminder(
            organization_id=org.id,
            type=ReminderType.custom,
            target_date=TODAY - timedelta(days=2),
            sent=True,
            telegram_message_id=999,
        )
        db.add(already_sent)
        db.commit()
    finally:
        db.close()

    sent_count = send_due_reminders_task.run()
    assert sent_count == 0
    assert len(sender.sent) == 0


def test_skips_organizations_without_linked_chat_without_raising(session_local, monkeypatch):
    sender = _RecordingSender()
    _patch_sender(monkeypatch, sender)
    monkeypatch.setattr("app.tasks.reminder_tasks.date", type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}))

    db = session_local()
    try:
        org = _make_org(db, "Без чата", telegram_chat_id=None)
        reminder = Reminder(
            organization_id=org.id, type=ReminderType.vehicle_inspection, target_date=TODAY
        )
        db.add(reminder)
        db.commit()
        reminder_id = reminder.id
    finally:
        db.close()

    sent_count = send_due_reminders_task.run()  # не должно упасть
    assert sent_count == 0

    db = session_local()
    try:
        assert db.get(Reminder, reminder_id).sent is False
    finally:
        db.close()


def test_is_idempotent_across_repeated_runs(session_local, monkeypatch):
    sender = _RecordingSender()
    _patch_sender(monkeypatch, sender)
    monkeypatch.setattr("app.tasks.reminder_tasks.date", type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}))

    db = session_local()
    try:
        org = _make_org(db, "Организация", telegram_chat_id=1)
        db.add(Reminder(organization_id=org.id, type=ReminderType.rto_deadline, target_date=TODAY))
        db.commit()
    finally:
        db.close()

    first_run = send_due_reminders_task.run()
    second_run = send_due_reminders_task.run()
    assert first_run == 1
    assert second_run == 0
    assert len(sender.sent) == 1


def test_organizations_are_isolated(session_local, monkeypatch):
    sender = _RecordingSender()
    _patch_sender(monkeypatch, sender)
    monkeypatch.setattr("app.tasks.reminder_tasks.date", type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}))

    db = session_local()
    try:
        org_a = _make_org(db, "Альфа", telegram_chat_id=1)
        org_b = _make_org(db, "Бета", telegram_chat_id=2)
        db.add(Reminder(organization_id=org_a.id, type=ReminderType.rto_deadline, target_date=TODAY))
        db.add(Reminder(organization_id=org_b.id, type=ReminderType.etrn_deadline, target_date=TODAY))
        db.commit()
    finally:
        db.close()

    sent_count = send_due_reminders_task.run()
    assert sent_count == 2

    db = session_local()
    try:
        for reminder in db.query(Reminder).all():
            assert reminder.sent is True
    finally:
        db.close()
