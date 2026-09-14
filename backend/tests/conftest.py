import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — регистрирует все модели в Base.metadata
from app.celery_app import celery_app
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app

# Роуты триггерят пересчёт РТО через recalculate_rto_for_driver_task.delay(...).
# В тестах нет брокера Redis — переводим Celery в eager-режим, чтобы .delay()
# выполнялся синхронно в процессе, как и прямые вызовы .run() в test_rto_tasks.py.
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_engine, monkeypatch):
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    # Роуты вызывают recalculate_rto_for_driver_task.delay(...), который в
    # eager-режиме выполняется синхронно и открывает сессию через
    # app.tasks.rto_tasks.SessionLocal — подменяем её на тестовую БД, иначе
    # таск попытается писать в боевой Postgres из settings.database_url.
    monkeypatch.setattr("app.tasks.rto_tasks.SessionLocal", testing_session_local)
    # Аналогично — периодический таск рассылки напоминаний (reminders.send_due)
    # тоже открывает свою сессию напрямую через SessionLocal, а не через
    # FastAPI dependency override.
    monkeypatch.setattr("app.tasks.reminder_tasks.SessionLocal", testing_session_local)
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


class FakeSmsSender:
    """Тестовая замена SmsSender — коды складываются в список вместо отправки."""

    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, phone: str, code: str) -> None:
        self.sent.append((phone, code))

    @property
    def last_code(self) -> str:
        return self.sent[-1][1]


@pytest.fixture()
def fake_sms(monkeypatch):
    sender = FakeSmsSender()
    monkeypatch.setattr("app.services.auth_service.get_sms_sender", lambda: sender)
    return sender


def register_and_login(client, fake_sms, phone: str = "+79990000001") -> dict:
    """Регистрирует новую организацию/пользователя через SMS-флоу и возвращает
    пару токенов. Общий помощник для тестов, которым нужен авторизованный клиент
    (worktime/violations/trips и т.п.), не связанных напрямую с проверкой auth-флоу."""
    resp = client.post("/api/auth/register/request-code", json={"phone": phone})
    assert resp.status_code == 204
    code = fake_sms.last_code
    resp = client.post(
        "/api/auth/register/confirm",
        json={
            "phone": phone,
            "code": code,
            "organization_name": "Тестовая организация",
            "user_name": "Тестовый пользователь",
        },
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture()
def auth_headers(client, fake_sms) -> dict:
    tokens = register_and_login(client, fake_sms)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
