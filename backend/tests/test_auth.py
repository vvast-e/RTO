"""
Интеграционные тесты аутентификации по SMS-коду.

Используют in-memory SQLite (см. tests/conftest.py) и FakeSmsSender вместо
реального SMS-агрегатора.
"""

from app.services import auth_service

PHONE = "+79991234567"


def register_flow(client, fake_sms, phone=PHONE, org_name="ИП Иванов", user_name="Иван Иванов"):
    resp = client.post("/api/auth/register/request-code", json={"phone": phone})
    assert resp.status_code == 204
    code = fake_sms.last_code
    resp = client.post(
        "/api/auth/register/confirm",
        json={
            "phone": phone,
            "code": code,
            "organization_name": org_name,
            "user_name": user_name,
        },
    )
    return resp


def test_register_success(client, fake_sms):
    resp = register_flow(client, fake_sms)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_register_request_code_twice_before_cooldown_is_rate_limited(client, fake_sms):
    resp1 = client.post("/api/auth/register/request-code", json={"phone": PHONE})
    assert resp1.status_code == 204
    resp2 = client.post("/api/auth/register/request-code", json={"phone": PHONE})
    assert resp2.status_code == 429


def test_login_success_for_existing_user(client, fake_sms):
    register_flow(client, fake_sms)

    resp = client.post("/api/auth/login/request-code", json={"phone": PHONE})
    assert resp.status_code == 204
    code = fake_sms.last_code

    resp = client.post("/api/auth/login/confirm", json={"phone": PHONE, "code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_request_code_for_unknown_phone_is_404(client, fake_sms):
    resp = client.post("/api/auth/login/request-code", json={"phone": PHONE})
    assert resp.status_code == 404


def test_login_confirm_with_wrong_code_is_rejected(client, fake_sms):
    register_flow(client, fake_sms)
    client.post("/api/auth/login/request-code", json={"phone": PHONE})

    resp = client.post("/api/auth/login/confirm", json={"phone": PHONE, "code": "000000"})
    assert resp.status_code == 400


def test_login_confirm_exceeding_attempt_limit_invalidates_code(client, fake_sms):
    register_flow(client, fake_sms)
    client.post("/api/auth/login/request-code", json={"phone": PHONE})
    correct_code = fake_sms.last_code

    for _ in range(auth_service.MAX_ATTEMPTS):
        resp = client.post("/api/auth/login/confirm", json={"phone": PHONE, "code": "000000"})
        assert resp.status_code == 400

    # даже с верным кодом дальше нельзя — попытки исчерпаны, код инвалидирован
    resp = client.post("/api/auth/login/confirm", json={"phone": PHONE, "code": correct_code})
    assert resp.status_code == 400


def test_verify_code_expired_raises(db_engine, fake_sms):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm import sessionmaker

    from app.models.phone_verification import VerificationPurpose

    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        auth_service.request_code(db, PHONE, VerificationPurpose.login)
        code = fake_sms.last_code
        # искусственно "состариваем" код
        from app.models.phone_verification import PhoneVerificationCode

        record = db.query(PhoneVerificationCode).order_by(
            PhoneVerificationCode.created_at.desc()
        ).first()
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        try:
            auth_service.verify_code(db, PHONE, code, VerificationPurpose.login)
            assert False, "ожидалась CodeExpiredError"
        except auth_service.CodeExpiredError:
            pass
    finally:
        db.close()


def test_register_duplicate_phone_is_conflict(client, fake_sms):
    register_flow(client, fake_sms)
    resp = client.post("/api/auth/register/request-code", json={"phone": PHONE})
    assert resp.status_code == 409


def test_refresh_token_returns_new_pair(client, fake_sms):
    tokens = register_flow(client, fake_sms).json()
    resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert "access_token" in new_tokens


def test_refresh_with_access_token_is_rejected(client, fake_sms):
    tokens = register_flow(client, fake_sms).json()
    resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401


def test_protected_route_requires_token(client, fake_sms):
    resp = client.get("/api/vehicles")
    assert resp.status_code == 401


def test_protected_route_works_with_valid_token(client, fake_sms):
    tokens = register_flow(client, fake_sms).json()
    resp = client.get(
        "/api/vehicles", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []
