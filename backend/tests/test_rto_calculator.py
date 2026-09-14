"""
Юнит-тесты RtoCalculator.

Нормативы в app.services.rto_rules сверены с Приказом Минтранса России
от 14.04.2026 № 160 (действует с 01.09.2026).
"""

from datetime import datetime, timedelta

from app.models.violation import ViolationType
from app.models.worktime import EntryType
from app.services.rto_calculator import RtoCalculator, WorkTimeEntryLike

BASE_DAY = datetime(2026, 9, 14, 6, 0)


def entry(entry_type: EntryType, start: datetime, hours: float) -> WorkTimeEntryLike:
    return WorkTimeEntryLike(
        entry_type=entry_type, start_time=start, end_time=start + timedelta(hours=hours)
    )


def test_no_violations_for_normal_day():
    entries = [
        entry(EntryType.driving, BASE_DAY, 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=4), 0.75),  # 45 мин перерыв
        entry(EntryType.driving, BASE_DAY + timedelta(hours=4.75), 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=8.75), 12.0),
    ]
    calc = RtoCalculator()
    assert calc.evaluate(entries) == []


def test_daily_driving_exceeded_warning():
    entries = [
        entry(EntryType.driving, BASE_DAY, 4.5),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=4.5), 0.75),
        entry(EntryType.driving, BASE_DAY + timedelta(hours=5.25), 5.0),  # итого 9.5ч
        entry(EntryType.rest, BASE_DAY + timedelta(hours=10.25), 12.0),
    ]
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    types = [v.violation_type for v in violations]
    assert ViolationType.daily_driving_exceeded in types


def test_daily_driving_exceeded_hard_violation():
    entries = [
        entry(EntryType.driving, BASE_DAY, 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=4), 0.75),
        entry(EntryType.driving, BASE_DAY + timedelta(hours=4.75), 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=8.75), 0.75),
        entry(EntryType.driving, BASE_DAY + timedelta(hours=9.5), 2.5),  # итого 10.5ч
        entry(EntryType.rest, BASE_DAY + timedelta(hours=12), 12.0),
    ]
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    hard = [
        v
        for v in violations
        if v.violation_type == ViolationType.daily_driving_exceeded
        and v.severity.value == "violation"
    ]
    assert len(hard) == 1


def test_continuous_driving_without_break():
    entries = [
        entry(EntryType.driving, BASE_DAY, 5.0),  # 5ч без перерыва > 4.5ч
        entry(EntryType.rest, BASE_DAY + timedelta(hours=5), 12.0),
    ]
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    assert any(
        v.violation_type == ViolationType.continuous_driving_exceeded for v in violations
    )


def test_short_break_does_not_reset_continuous_timer():
    entries = [
        entry(EntryType.driving, BASE_DAY, 3.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=3), 0.2),  # 12 мин — недостаточно
        entry(EntryType.driving, BASE_DAY + timedelta(hours=3.2), 2.0),  # суммарно 5ч
        entry(EntryType.rest, BASE_DAY + timedelta(hours=5.2), 12.0),
    ]
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    assert any(
        v.violation_type == ViolationType.continuous_driving_exceeded for v in violations
    )


def test_short_break_between_driving_segments_is_not_daily_rest():
    """Регрессия: короткий 45-минутный перерыв между отрезками вождения в
    течение одного дня не должен засчитываться как недостаточный ежедневный
    отдых — нормативу 9–11 ч подчиняется только отдых, завершающий день."""
    entries = [
        entry(EntryType.driving, BASE_DAY, 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=4), 0.75),  # 45 мин — не ежедневный отдых
        entry(EntryType.driving, BASE_DAY + timedelta(hours=4.75), 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=8.75), 6.0),  # а вот это уже недостаточно
    ]
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    daily_rest_violations = [
        v for v in violations if v.violation_type == ViolationType.daily_rest_insufficient
    ]
    assert len(daily_rest_violations) == 1


def test_insufficient_daily_rest():
    entries = [
        entry(EntryType.driving, BASE_DAY, 4.0),
        entry(EntryType.rest, BASE_DAY + timedelta(hours=4), 7.0),  # меньше 9ч сокращённого
    ]
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    assert any(v.violation_type == ViolationType.daily_rest_insufficient for v in violations)


def test_biweekly_driving_exceeded():
    entries = []
    for day in range(13):
        start = BASE_DAY + timedelta(days=day)
        entries.append(entry(EntryType.driving, start, 8.0))  # 13*8 = 104ч > 90ч
        entries.append(entry(EntryType.rest, start + timedelta(hours=8), 12.0))
    calc = RtoCalculator()
    violations = calc.evaluate(entries)
    assert any(v.violation_type == ViolationType.biweekly_driving_exceeded for v in violations)
