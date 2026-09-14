"""Интеграционные тесты POST /api/worktime/import."""

CSV_HEADER = "ФИО;Номер карты;Тип активности;Начало;Окончание\n"


def create_driver(client, auth_headers, full_name="Иван Петров", card_number=None):
    payload = {"full_name": full_name}
    if card_number is not None:
        payload["tachograph_card_number"] = card_number
    resp = client.post("/api/drivers", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def _upload(client, auth_headers, content: bytes, filename="export.csv"):
    return client.post(
        "/api/worktime/import",
        headers=auth_headers,
        files={"file": (filename, content, "text/csv")},
    )


def test_import_creates_entries_for_matched_driver(client, auth_headers):
    driver = create_driver(client, auth_headers, "Иван Петров", card_number="123")
    content = (
        CSV_HEADER
        + "Иван Петров;123;вождение;14.09.2026 06:00;14.09.2026 10:00\n"
        + "Иван Петров;123;отдых;14.09.2026 10:00;14.09.2026 10:45\n"
    ).encode("utf-8-sig")

    resp = _upload(client, auth_headers, content)
    assert resp.status_code == 200
    report = resp.json()
    assert report["created"] == 2
    assert report["failed"] == 0
    assert report["skipped_duplicates"] == 0

    resp = client.get("/api/worktime", params={"driver_id": driver["id"]}, headers=auth_headers)
    entries = resp.json()
    assert len(entries) == 2
    assert all(e["source"] == "import" for e in entries)


def test_import_matches_driver_by_full_name_without_card(client, auth_headers):
    create_driver(client, auth_headers, "Пётр Сидоров")
    content = (
        CSV_HEADER + "Пётр Сидоров;;вождение;14.09.2026 06:00;14.09.2026 10:00\n"
    ).encode("utf-8")

    resp = _upload(client, auth_headers, content)
    assert resp.status_code == 200
    report = resp.json()
    assert report["created"] == 1


def test_import_same_file_twice_creates_no_duplicates(client, auth_headers):
    create_driver(client, auth_headers, "Иван Петров", card_number="123")
    content = (
        CSV_HEADER + "Иван Петров;123;вождение;14.09.2026 06:00;14.09.2026 10:00\n"
    ).encode("utf-8")

    first = _upload(client, auth_headers, content)
    assert first.json()["created"] == 1

    second = _upload(client, auth_headers, content)
    report = second.json()
    assert report["created"] == 0
    assert report["skipped_duplicates"] == 1

    resp = client.get("/api/worktime", headers=auth_headers)
    assert len(resp.json()) == 1


def test_import_unknown_driver_reported_as_error(client, auth_headers):
    content = (
        CSV_HEADER + "Незнакомец;;вождение;14.09.2026 06:00;14.09.2026 10:00\n"
    ).encode("utf-8")

    resp = _upload(client, auth_headers, content)
    assert resp.status_code == 200
    report = resp.json()
    assert report["created"] == 0
    assert report["failed"] == 1
    assert "Незнакомец" in report["errors"][0]["reason"]


def test_import_ambiguous_full_name_reported_as_error(client, auth_headers):
    create_driver(client, auth_headers, "Иван Петров", card_number="111")
    create_driver(client, auth_headers, "Иван Петров", card_number="222")
    content = (
        CSV_HEADER + "Иван Петров;;вождение;14.09.2026 06:00;14.09.2026 10:00\n"
    ).encode("utf-8")

    resp = _upload(client, auth_headers, content)
    report = resp.json()
    assert report["created"] == 0
    assert report["failed"] == 1


def test_import_broken_file_returns_400(client, auth_headers):
    resp = _upload(client, auth_headers, b"\x00\x01not a real file", filename="export.xlsx")
    assert resp.status_code == 400


def test_import_unsupported_extension_returns_400(client, auth_headers):
    resp = _upload(client, auth_headers, b"data", filename="export.txt")
    assert resp.status_code == 400


def test_import_requires_auth(client):
    resp = client.post(
        "/api/worktime/import",
        files={"file": ("export.csv", (CSV_HEADER).encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 401
