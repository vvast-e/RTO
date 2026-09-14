import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.driver import Driver
from app.models.trip import Trip
from app.models.worktime import EntrySource, WorkTimeEntry
from app.schemas.worktime import WorkTimeEntryCreate, WorkTimeEntryOut
from app.schemas.worktime_import import WorktimeImportReport, WorktimeImportRowError
from app.services.tachograph_import import UnsupportedFileFormatError, parse_file
from app.tasks.rto_tasks import recalculate_rto_for_driver_task

router = APIRouter(prefix="/api/worktime", tags=["worktime"])


def _get_owned_driver(driver_id: uuid.UUID, org_id: uuid.UUID, db: Session) -> Driver:
    driver = db.get(Driver, driver_id)
    if not driver or driver.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    return driver


@router.get("", response_model=list[WorkTimeEntryOut])
def list_worktime_entries(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    driver_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    stmt = (
        select(WorkTimeEntry)
        .join(Driver, WorkTimeEntry.driver_id == Driver.id)
        .where(Driver.organization_id == org_id)
    )
    if driver_id is not None:
        stmt = stmt.where(WorkTimeEntry.driver_id == driver_id)
    stmt = stmt.order_by(WorkTimeEntry.start_time).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=WorkTimeEntryOut, status_code=201)
def create_worktime_entry(
    payload: WorkTimeEntryCreate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    _get_owned_driver(payload.driver_id, org_id, db)
    if payload.trip_id is not None:
        trip = db.get(Trip, payload.trip_id)
        if not trip or trip.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Рейс не найден")
    entry = WorkTimeEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)

    period_end = (entry.end_time or entry.start_time) + timedelta(seconds=1)
    recalculate_rto_for_driver_task.delay(
        str(entry.driver_id), entry.start_time.isoformat(), period_end.isoformat()
    )
    return entry


@router.get("/{entry_id}", response_model=WorkTimeEntryOut)
def get_worktime_entry(
    entry_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    entry = db.get(WorkTimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    _get_owned_driver(entry.driver_id, org_id, db)
    return entry


def _build_driver_lookup(org_id: uuid.UUID, db: Session) -> tuple[dict[str, Driver], dict[str, list[Driver]]]:
    """Строит индексы водителей организации для сопоставления строк импорта:
    по номеру карты (уникально) и по нормализованному ФИО (может быть несколько
    водителей с одинаковым ФИО — тогда сопоставление по имени неоднозначно)."""
    drivers = db.execute(select(Driver).where(Driver.organization_id == org_id)).scalars().all()
    by_card: dict[str, Driver] = {}
    by_name: dict[str, list[Driver]] = {}
    for driver in drivers:
        if driver.tachograph_card_number:
            by_card[driver.tachograph_card_number.strip()] = driver
        name_key = driver.full_name.strip().lower()
        by_name.setdefault(name_key, []).append(driver)
    return by_card, by_name


@router.post("/import", response_model=WorktimeImportReport)
def import_worktime_entries(
    file: UploadFile,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """Импортирует записи WorkTimeEntry из CSV/Excel-выгрузки тахографа.

    Сопоставление водителя: сначала по номеру карты (Driver.tachograph_card_number),
    при отсутствии совпадения — по ФИО (Driver.full_name, без учёта регистра).
    Строка без однозначного совпадения по водителю попадает в отчёт как ошибка,
    запись не создаётся.

    Идемпотентность: запись с уже существующим сочетанием
    (driver_id, entry_type, start_time, end_time) — включая уже импортированные
    ранее из этого же файла — не создаётся повторно, а считается пропущенным
    дубликатом. Это же правило действует и внутри одного файла (дубли строк).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Не передано имя файла")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Пустой файл")

    try:
        parse_result = parse_file(file.filename, content)
    except UnsupportedFileFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл — повреждён или не соответствует формату")

    errors = [
        WorktimeImportRowError(row_number=e.row_number, reason=e.reason)
        for e in parse_result.errors
    ]

    by_card, by_name = _build_driver_lookup(org_id, db)

    existing_stmt = select(
        WorkTimeEntry.driver_id,
        WorkTimeEntry.entry_type,
        WorkTimeEntry.start_time,
        WorkTimeEntry.end_time,
    ).join(Driver, WorkTimeEntry.driver_id == Driver.id).where(Driver.organization_id == org_id)
    seen: set[tuple] = {
        (row.driver_id, row.entry_type, row.start_time, row.end_time)
        for row in db.execute(existing_stmt)
    }

    created_entries: list[WorkTimeEntry] = []
    for row in parse_result.rows:
        driver: Driver | None = None
        if row.card_number and row.card_number in by_card:
            driver = by_card[row.card_number]
        else:
            candidates = by_name.get(row.full_name.strip().lower(), [])
            if len(candidates) == 1:
                driver = candidates[0]
            elif len(candidates) > 1:
                errors.append(
                    WorktimeImportRowError(
                        row_number=row.row_number,
                        reason=f"Несколько водителей с ФИО '{row.full_name}' — уточните номер карты",
                    )
                )
                continue

        if driver is None:
            errors.append(
                WorktimeImportRowError(
                    row_number=row.row_number,
                    reason=f"Водитель не найден: '{row.full_name}'"
                    + (f" (карта {row.card_number})" if row.card_number else ""),
                )
            )
            continue

        dedup_key = (driver.id, row.entry_type, row.start_time, row.end_time)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        entry = WorkTimeEntry(
            driver_id=driver.id,
            entry_type=row.entry_type,
            start_time=row.start_time,
            end_time=row.end_time,
            source=EntrySource.import_file,
        )
        db.add(entry)
        created_entries.append(entry)

    db.commit()
    for entry in created_entries:
        db.refresh(entry)

    entries_by_driver: dict[uuid.UUID, list[WorkTimeEntry]] = {}
    for entry in created_entries:
        entries_by_driver.setdefault(entry.driver_id, []).append(entry)
    for driver_id, driver_entries in entries_by_driver.items():
        period_start = min(e.start_time for e in driver_entries)
        period_end = max(e.end_time or e.start_time for e in driver_entries) + timedelta(seconds=1)
        recalculate_rto_for_driver_task.delay(
            str(driver_id), period_start.isoformat(), period_end.isoformat()
        )

    skipped_duplicates = len(parse_result.rows) - len(created_entries) - (
        len(errors) - len(parse_result.errors)
    )

    return WorktimeImportReport(
        created=len(created_entries),
        skipped_duplicates=skipped_duplicates,
        failed=len(errors),
        errors=errors,
        created_entry_ids=[e.id for e in created_entries],
    )
