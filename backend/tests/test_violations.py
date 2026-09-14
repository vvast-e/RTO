"""Интеграционные тесты GET /api/violations (список + фильтры)."""

from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from app.models.driver import Driver
from app.models.violation import RtoViolation, ViolationSeverity, ViolationType

BASE_DAY = datetime(2026, 9, 14, 6, 0)


def create_driver(client, auth_headers, full_name="Иван Петров"):
    resp = client.post("/api/drivers", json={"full_name": full_name}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def _add_violation(db, driver_id, detected_at, severity, resolved=False):
    violation = RtoViolation(
        driver_id=driver_id,
        violation_type=ViolationType.continuous_driving_exceeded,
        severity=severity,
        detected_at=detected_at,
        description="тест",
        resolved=resolved,
    )
    db.add(violation)
    db.commit()
    return violation


def test_list_violations_for_own_organization(client, auth_headers, db_engine):
    driver = create_driver(client, auth_headers)
    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        import uuid

        _add_violation(db, uuid.UUID(driver["id"]), BASE_DAY, ViolationSeverity.violation)
    finally:
        db.close()

    resp = client.get("/api/violations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["driver_id"] == driver["id"]


def test_list_violations_filtered_by_severity_and_resolved(client, auth_headers, db_engine):
    driver = create_driver(client, auth_headers)
    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        import uuid

        driver_uuid = uuid.UUID(driver["id"])
        _add_violation(db, driver_uuid, BASE_DAY, ViolationSeverity.warning, resolved=False)
        _add_violation(
            db, driver_uuid, BASE_DAY + timedelta(days=1), ViolationSeverity.violation, resolved=True
        )
    finally:
        db.close()

    resp = client.get(
        "/api/violations", params={"severity": "violation", "resolved": "true"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["severity"] == "violation"
    assert data[0]["resolved"] is True

    resp = client.get("/api/violations", params={"resolved": "false"}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_violations_does_not_leak_other_organizations(client, fake_sms, auth_headers, db_engine):
    driver = create_driver(client, auth_headers)
    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        import uuid

        _add_violation(db, uuid.UUID(driver["id"]), BASE_DAY, ViolationSeverity.violation)
    finally:
        db.close()

    from tests.conftest import register_and_login

    other_tokens = register_and_login(client, fake_sms, phone="+79990000003")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.get("/api/violations", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_violations_requires_auth(client):
    resp = client.get("/api/violations")
    assert resp.status_code == 401
