"""Генерация PDF путевого листа.

Точная форма путевого листа для грузового транспорта РФ пользователем пока
не подтверждена (открытый вопрос ТЗ — см. память проекта). Реализован
минимальный, но содержательный макет: шапка организации, ФИО водителя,
гос.номер и марка автомобиля, номер документа, дата выдачи, маршрут и даты
рейса. Если форма будет уточнена — верстку достаточно поменять в одном
месте (build_waybill_html), сам механизм рендера и сохранения не изменится.

WeasyPrint выбран, т.к. уже был заложен в requirements.txt и Dockerfile
(системные пакеты pango/cairo/gdk-pixbuf уже установлены) — сторонних
зависимостей это не добавляет.
"""

import uuid
from pathlib import Path

from app.core.config import settings
from app.models.driver import Driver
from app.models.organization import Organization
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.models.waybill import Waybill


def _pdf_dir() -> Path:
    path = Path(settings.waybill_pdf_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_waybill_html(
    waybill: Waybill, trip: Trip, driver: Driver, vehicle: Vehicle, organization: Organization
) -> str:
    def esc(value) -> str:
        return "" if value is None else str(value).replace("<", "&lt;").replace(">", "&gt;")

    return f"""
    <html>
    <head><meta charset="utf-8"><style>
        body {{ font-family: sans-serif; font-size: 12px; }}
        h1 {{ font-size: 16px; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        td, th {{ border: 1px solid #333; padding: 4px 8px; text-align: left; }}
    </style></head>
    <body>
        <h1>Путевой лист № {esc(waybill.document_number)}</h1>
        <p>Организация: {esc(organization.name)} (ИНН {esc(organization.inn)})</p>
        <p>Дата выдачи: {esc(waybill.issue_date.isoformat())}</p>
        <table>
            <tr><th>Водитель</th><td>{esc(driver.full_name)}</td></tr>
            <tr><th>Автомобиль</th><td>{esc(vehicle.brand_model)}, гос.номер {esc(vehicle.plate_number)}</td></tr>
            <tr><th>Маршрут</th><td>{esc(trip.start_location)} — {esc(trip.end_location)}</td></tr>
            <tr><th>Дата/время выезда</th><td>{esc(trip.start_datetime)}</td></tr>
            <tr><th>Дата/время возвращения</th><td>{esc(trip.end_datetime)}</td></tr>
            <tr><th>Пробег, км</th><td>{esc(trip.distance_km)}</td></tr>
        </table>
    </body>
    </html>
    """


def _write_pdf(html: str, file_path: Path) -> None:
    """Тонкая обёртка вокруг WeasyPrint. Импорт лежит внутри функции, а не на
    уровне модуля: WeasyPrint требует нативные библиотеки pango/gobject
    (см. backend/Dockerfile), которых нет на Windows-машине разработчика без
    отдельной установки GTK — модуль всё равно должен импортироваться (и
    маршрут /api/waybills — регистрироваться) в таком окружении. В тестах эта
    функция подменяется (см. backend/tests/test_waybills.py), поэтому
    реальный вызов WeasyPrint происходит только в docker-контейнере (Linux,
    системные библиотеки установлены)."""
    from weasyprint import HTML

    HTML(string=html).write_pdf(str(file_path))


def generate_waybill_pdf(
    waybill: Waybill, trip: Trip, driver: Driver, vehicle: Vehicle, organization: Organization
) -> str:
    """Рендерит PDF и сохраняет на диск. Возвращает путь (пригодный для
    записи в Waybill.pdf_file_url)."""

    html = build_waybill_html(waybill, trip, driver, vehicle, organization)
    filename = f"{waybill.id}-{uuid.uuid4().hex[:8]}.pdf"
    file_path = _pdf_dir() / filename
    _write_pdf(html, file_path)
    return str(file_path)
