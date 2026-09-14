"""Интеграционные тесты: запись WorkTimeEntry (вручную или импортом) должна
триггерить синхронный пересчёт РТО и создавать RtoViolation."""


def create_driver(client, auth_headers, full_name="Иван Петров", card_number=None):
    payload = {"full_name": full_name}
    if card_number is not None:
        payload["tachograph_card_number"] = card_number
    resp = client.post("/api/drivers", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def test_manual_worktime_entry_triggers_recalc_and_creates_violation(client, auth_headers):
    driver = create_driver(client, auth_headers)

    # 5 ч непрерывного вождения без перерыва — превышает норматив непрерывного
    # управления (см. test_rto_tasks.py, тот же сценарий даёт 1 нарушение).
    resp = client.post(
        "/api/worktime",
        json={
            "driver_id": driver["id"],
            "entry_type": "driving",
            "start_time": "2026-09-14T06:00:00Z",
            "end_time": "2026-09-14T11:00:00Z",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = client.get("/api/violations", params={"driver_id": driver["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    violations = resp.json()
    assert len(violations) == 1
    assert violations[0]["violation_type"] == "continuous_driving_exceeded"


def test_import_triggers_recalc_and_creates_violation(client, auth_headers):
    create_driver(client, auth_headers, "Иван Петров", card_number="123")
    content = (
        "ФИО;Номер карты;Тип активности;Начало;Окончание\n"
        "Иван Петров;123;вождение;14.09.2026 06:00;14.09.2026 11:00\n"
    ).encode("utf-8-sig")

    resp = client.post(
        "/api/worktime/import",
        headers=auth_headers,
        files={"file": ("export.csv", content, "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1

    resp = client.get("/api/violations", headers=auth_headers)
    assert resp.status_code == 200
    violations = resp.json()
    assert len(violations) == 1
    assert violations[0]["violation_type"] == "continuous_driving_exceeded"
