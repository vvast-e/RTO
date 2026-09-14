"""
Связывает RtoCalculator с БД: берёт WorkTimeEntry водителя за период,
прогоняет через RtoCalculator и идемпотентно сохраняет найденные
нарушения как RtoViolation.

Вынесено отдельно от Celery-таска (app.tasks.rto_tasks), чтобы функцию
можно было вызывать синхронно в тестах без брокера.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.violation import RtoViolation
from app.models.worktime import WorkTimeEntry
from app.services.rto_calculator import RtoCalculator, WorkTimeEntryLike


def recalculate_rto_for_driver(
    db: Session,
    driver_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
) -> list[RtoViolation]:
    """Пересчитывает нарушения РТО для одного водителя за [period_start, period_end).

    Идемпотентность: перед вставкой каждая найденная кандидатура нарушения
    проверяется на дубликат по (driver_id, violation_type, detected_at) —
    повторный запуск для того же периода и тех же данных не создаёт
    дублирующихся записей RtoViolation.
    """
    entries_stmt = select(WorkTimeEntry).where(
        WorkTimeEntry.driver_id == driver_id,
        WorkTimeEntry.start_time >= period_start,
        WorkTimeEntry.start_time < period_end,
    )
    entries = db.execute(entries_stmt).scalars().all()

    entry_likes = [
        WorkTimeEntryLike(
            entry_type=e.entry_type,
            start_time=e.start_time,
            end_time=e.end_time,
            trip_id=str(e.trip_id) if e.trip_id else None,
        )
        for e in entries
    ]
    candidates = RtoCalculator().evaluate(entry_likes)

    created: list[RtoViolation] = []
    for candidate in candidates:
        exists_stmt = select(RtoViolation).where(
            RtoViolation.driver_id == driver_id,
            RtoViolation.violation_type == candidate.violation_type,
            RtoViolation.detected_at == candidate.detected_at,
        )
        if db.execute(exists_stmt).scalar_one_or_none() is not None:
            continue

        trip_id = uuid.UUID(candidate.trip_id) if candidate.trip_id else None
        violation = RtoViolation(
            driver_id=driver_id,
            trip_id=trip_id,
            violation_type=candidate.violation_type,
            severity=candidate.severity,
            detected_at=candidate.detected_at,
            description=candidate.description,
        )
        db.add(violation)
        created.append(violation)

    db.commit()
    for violation in created:
        db.refresh(violation)
    return created
