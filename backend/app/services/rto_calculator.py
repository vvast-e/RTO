"""
RtoCalculator — чистый расчётный движок режима труда и отдыха.

На вход подаётся список WorkTimeEntry (dict-подобные объекты с полями
entry_type/start_time/end_time) для одного водителя за период,
на выходе — список найденных нарушений (ViolationCandidate).

Реализован как чистая функция без побочных эффектов и без обращения к БД,
чтобы было просто покрыть юнит-тестами. Привязка ViolationCandidate к
модели RtoViolation и запись в БД — на уровне вызывающего кода (Celery-таск).

ВАЖНО: нормативы в app.services.rto_rules — НЕ ПРОВЕРЕНЫ, см. TODO там.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.violation import ViolationSeverity, ViolationType
from app.models.worktime import EntryType
from app.services.rto_rules import DEFAULT_RULES, RtoRules


@dataclass(frozen=True)
class WorkTimeEntryLike:
    entry_type: EntryType
    start_time: datetime
    end_time: datetime | None
    trip_id: str | None = None

    @property
    def duration_hours(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() / 3600


@dataclass(frozen=True)
class ViolationCandidate:
    violation_type: ViolationType
    severity: ViolationSeverity
    detected_at: datetime
    description: str
    trip_id: str | None = None


class RtoCalculator:
    def __init__(self, rules: RtoRules = DEFAULT_RULES):
        self.rules = rules

    def evaluate(self, entries: list[WorkTimeEntryLike]) -> list[ViolationCandidate]:
        """Прогоняет все проверки над отсортированным списком записей одного водителя."""
        sorted_entries = sorted(entries, key=lambda e: e.start_time)
        violations: list[ViolationCandidate] = []

        violations += self._check_daily_driving(sorted_entries)
        violations += self._check_continuous_driving(sorted_entries)
        violations += self._check_daily_rest(sorted_entries)
        violations += self._check_biweekly_driving(sorted_entries)

        return violations

    def _driving_entries_by_day(self, entries: list[WorkTimeEntryLike]):
        by_day: dict[str, list[WorkTimeEntryLike]] = {}
        for e in entries:
            if e.entry_type != EntryType.driving:
                continue
            key = e.start_time.date().isoformat()
            by_day.setdefault(key, []).append(e)
        return by_day

    def _check_daily_driving(self, entries: list[WorkTimeEntryLike]) -> list[ViolationCandidate]:
        violations = []
        for day, day_entries in self._driving_entries_by_day(entries).items():
            total_hours = sum(e.duration_hours for e in day_entries)
            if total_hours > self.rules.max_daily_driving_hours_extended:
                violations.append(
                    ViolationCandidate(
                        violation_type=ViolationType.daily_driving_exceeded,
                        severity=ViolationSeverity.violation,
                        detected_at=day_entries[-1].end_time or day_entries[-1].start_time,
                        description=(
                            f"Суммарное время управления за {day} составило "
                            f"{total_hours:.1f} ч — превышен максимум "
                            f"{self.rules.max_daily_driving_hours_extended} ч."
                        ),
                    )
                )
            elif total_hours > self.rules.max_daily_driving_hours:
                violations.append(
                    ViolationCandidate(
                        violation_type=ViolationType.daily_driving_exceeded,
                        severity=ViolationSeverity.warning,
                        detected_at=day_entries[-1].end_time or day_entries[-1].start_time,
                        description=(
                            f"Время управления за {day} составило {total_hours:.1f} ч "
                            f"— выше базового лимита {self.rules.max_daily_driving_hours} ч "
                            "(допустимо не более 2 раз в неделю)."
                        ),
                    )
                )
        return violations

    def _check_continuous_driving(
        self, entries: list[WorkTimeEntryLike]
    ) -> list[ViolationCandidate]:
        violations = []
        continuous_hours = 0.0
        for e in entries:
            if e.entry_type == EntryType.driving:
                continuous_hours += e.duration_hours
                if continuous_hours > self.rules.max_continuous_driving_hours:
                    violations.append(
                        ViolationCandidate(
                            violation_type=ViolationType.continuous_driving_exceeded,
                            severity=ViolationSeverity.violation,
                            detected_at=e.end_time or e.start_time,
                            description=(
                                f"Непрерывное управление составило {continuous_hours:.1f} ч "
                                f"без перерыва ≥{self.rules.min_break_after_continuous_minutes} мин."
                            ),
                            trip_id=e.trip_id,
                        )
                    )
                    continuous_hours = 0.0
            else:
                break_minutes = e.duration_hours * 60
                if break_minutes >= self.rules.min_break_after_continuous_minutes:
                    continuous_hours = 0.0
        return violations

    def _check_daily_rest(self, entries: list[WorkTimeEntryLike]) -> list[ViolationCandidate]:
        """Проверяет норматив ежедневного отдыха (9–11 ч).

        Этому нормативу подчиняется только отдых, завершающий рабочий день —
        то есть идущий сразу после ПОСЛЕДНЕГО за календарный день отрезка
        вождения. Короткие перерывы между отрезками вождения в течение
        одного дня (напр. обязательные 45 мин после непрерывного вождения)
        покрываются отдельным нормативом min_break_after_continuous_minutes
        и не должны засчитываться как недостаточный ежедневный отдых.
        """
        violations = []
        last_driving_idx_by_day: dict[str, int] = {}
        for idx, e in enumerate(entries):
            if e.entry_type == EntryType.driving:
                last_driving_idx_by_day[e.start_time.date().isoformat()] = idx

        for idx in last_driving_idx_by_day.values():
            if idx + 1 >= len(entries):
                continue
            nxt = entries[idx + 1]
            if nxt.entry_type == EntryType.rest:
                rest_hours = nxt.duration_hours
                if rest_hours < self.rules.min_daily_rest_hours_reduced:
                    violations.append(
                        ViolationCandidate(
                            violation_type=ViolationType.daily_rest_insufficient,
                            severity=ViolationSeverity.violation,
                            detected_at=nxt.end_time or nxt.start_time,
                            description=(
                                f"Ежедневный отдых {rest_hours:.1f} ч меньше минимального "
                                f"сокращённого {self.rules.min_daily_rest_hours_reduced} ч."
                            ),
                        )
                    )
                elif rest_hours < self.rules.min_daily_rest_hours:
                    violations.append(
                        ViolationCandidate(
                            violation_type=ViolationType.daily_rest_insufficient,
                            severity=ViolationSeverity.warning,
                            detected_at=nxt.end_time or nxt.start_time,
                            description=(
                                f"Ежедневный отдых {rest_hours:.1f} ч меньше базовых "
                                f"{self.rules.min_daily_rest_hours} ч (допустим сокращённый "
                                "вариант с компенсацией)."
                            ),
                        )
                    )
        return violations

    def _check_biweekly_driving(
        self, entries: list[WorkTimeEntryLike]
    ) -> list[ViolationCandidate]:
        violations = []
        driving_entries = [e for e in entries if e.entry_type == EntryType.driving]
        if not driving_entries:
            return violations

        window_start = driving_entries[0].start_time
        window_end = window_start + timedelta(days=14)
        total = sum(
            e.duration_hours for e in driving_entries if window_start <= e.start_time < window_end
        )
        if total > self.rules.max_biweekly_driving_hours:
            violations.append(
                ViolationCandidate(
                    violation_type=ViolationType.biweekly_driving_exceeded,
                    severity=ViolationSeverity.violation,
                    detected_at=driving_entries[-1].end_time or driving_entries[-1].start_time,
                    description=(
                        f"Суммарное управление за 2 недели с {window_start.date()} составило "
                        f"{total:.1f} ч — превышен лимит {self.rules.max_biweekly_driving_hours} ч."
                    ),
                )
            )
        return violations
