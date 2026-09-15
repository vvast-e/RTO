"""Интеграционные тесты /api/waybills: CRUD, изоляция по организации через
Trip, переход draft -> issued, генерация PDF."""

from pathlib import Path

import pytest

from app.core.config import settings
from tests.conftest import register_and_login


@pytest.fixture()
def waybill_pdf_dir(tmp_path, monkeypatch):
    """Генерация PDF пишет на диск — направляем её во временную папку теста
    вместо backend/generated/waybills, чтобы тесты не оставляли файлы в
    рабочей директории репозитория."""
    monkeypatch.setattr(settings, "waybill_pdf_dir", str(tmp_path))
    return tmp_path


@pytest.fixture()
def fake_pdf_writer(monkeypatch):
    """WeasyPrint требует нативные библиотеки pango/gobject, которых нет на
    Windows-машине разработчика (см. комментарий в
    app/services/waybill_pdf.py) — подменяем рендер на запись заглушки,
    чтобы проверить именно логику эндпоинта (файл создан, pdf_file_url
    проставлен), а не сам WeasyPrint."""

    def fake_write_pdf(html: str, file_path: Path) -> None:
        file_path.write_bytes(b"%PDF-1.4 fake\n")

    monkeypatch.setattr("app.services.waybill_pdf._write_pdf", fake_write_pdf)


def _create_trip(client, headers) -> str:
    driver_resp = client.post(
        "/api/drivers", json={"full_name": "Иванов Иван Иванович"}, headers=headers
    )
    driver_id = driver_resp.json()["id"]
    vehicle_resp = client.post(
        "/api/vehicles",
        json={"plate_number": "А123ВС77", "brand_model": "КАМАЗ 5490"},
        headers=headers,
    )
    vehicle_id = vehicle_resp.json()["id"]
    trip_resp = client.post(
        "/api/trips",
        json={
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "start_datetime": "2026-09-15T08:00:00Z",
            "end_datetime": "2026-09-15T18:00:00Z",
            "start_location": "Москва",
            "end_location": "Тверь",
            "distance_km": 180.5,
        },
        headers=headers,
    )
    assert trip_resp.status_code == 201
    return trip_resp.json()["id"]


def test_create_waybill(client, auth_headers):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-001", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["trip_id"] == trip_id
    assert data["document_number"] == "ПЛ-001"
    assert data["status"] == "draft"
    assert data["pdf_file_url"] is None


def test_waybills_require_auth(client):
    resp = client.get("/api/waybills")
    assert resp.status_code == 401


def test_create_waybill_for_foreign_trip_is_404(client, fake_sms, auth_headers):
    trip_id = _create_trip(client, auth_headers)

    other_tokens = register_and_login(client, fake_sms, phone="+79990000010")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-002", "issue_date": "2026-09-15"},
        headers=other_headers,
    )
    assert resp.status_code == 404


def test_list_waybills_filtered_by_trip_and_isolated_by_organization(client, fake_sms, auth_headers):
    trip_id = _create_trip(client, auth_headers)
    client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-003", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )

    resp = client.get("/api/waybills", params={"trip_id": trip_id}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    other_tokens = register_and_login(client, fake_sms, phone="+79990000011")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    resp = client.get("/api/waybills", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_waybill_for_foreign_organization_is_404(client, fake_sms, auth_headers):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-004", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    waybill_id = resp.json()["id"]

    other_tokens = register_and_login(client, fake_sms, phone="+79990000012")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    resp = client.get(f"/api/waybills/{waybill_id}", headers=other_headers)
    assert resp.status_code == 404


def test_issue_waybill_transitions_draft_to_issued(client, auth_headers):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-005", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    waybill_id = resp.json()["id"]

    resp = client.post(f"/api/waybills/{waybill_id}/issue", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "issued"

    # Повторный вызов идемпотентен, не ошибка.
    resp = client.post(f"/api/waybills/{waybill_id}/issue", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "issued"


def test_generate_waybill_pdf_creates_file_and_sets_url(
    client, auth_headers, waybill_pdf_dir, fake_pdf_writer
):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-006", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    waybill_id = resp.json()["id"]

    resp = client.post(f"/api/waybills/{waybill_id}/generate", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pdf_file_url"] is not None

    generated_files = list(waybill_pdf_dir.iterdir())
    assert len(generated_files) == 1
    assert Path(data["pdf_file_url"]) == generated_files[0]


def test_generate_waybill_pdf_for_unknown_waybill_is_404(client, auth_headers):
    resp = client.post(
        "/api/waybills/00000000-0000-0000-0000-000000000000/generate", headers=auth_headers
    )
    assert resp.status_code == 404


def test_download_waybill_pdf_after_generate(
    client, auth_headers, waybill_pdf_dir, fake_pdf_writer
):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-007", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    waybill_id = resp.json()["id"]
    client.post(f"/api/waybills/{waybill_id}/generate", headers=auth_headers)

    resp = client.get(f"/api/waybills/{waybill_id}/pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-1.4 fake\n"


def test_download_waybill_pdf_before_generate_is_404(client, auth_headers):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-008", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    waybill_id = resp.json()["id"]

    resp = client.get(f"/api/waybills/{waybill_id}/pdf", headers=auth_headers)
    assert resp.status_code == 404


def test_download_waybill_pdf_for_foreign_organization_is_404(
    client, fake_sms, auth_headers, waybill_pdf_dir, fake_pdf_writer
):
    trip_id = _create_trip(client, auth_headers)
    resp = client.post(
        "/api/waybills",
        json={"trip_id": trip_id, "document_number": "ПЛ-009", "issue_date": "2026-09-15"},
        headers=auth_headers,
    )
    waybill_id = resp.json()["id"]
    client.post(f"/api/waybills/{waybill_id}/generate", headers=auth_headers)

    other_tokens = register_and_login(client, fake_sms, phone="+79990000013")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    resp = client.get(f"/api/waybills/{waybill_id}/pdf", headers=other_headers)
    assert resp.status_code == 404
