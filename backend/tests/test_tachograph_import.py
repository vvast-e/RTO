"""Юнит-тесты парсера универсальной CSV/Excel-выгрузки тахографа."""

import io

from openpyxl import Workbook

from app.models.worktime import EntryType
from app.services.tachograph_import import UnsupportedFileFormatError, parse_file

CSV_HEADER = "ФИО;Номер карты;Тип активности;Начало;Окончание\n"


def test_parse_csv_valid_rows():
    content = (
        CSV_HEADER
        + "Иван Петров;123;вождение;14.09.2026 06:00;14.09.2026 10:00\n"
        + "Иван Петров;123;отдых;14.09.2026 10:00;14.09.2026 10:45\n"
    ).encode("utf-8-sig")

    result = parse_file("export.csv", content)

    assert result.errors == []
    assert len(result.rows) == 2
    assert result.rows[0].full_name == "Иван Петров"
    assert result.rows[0].card_number == "123"
    assert result.rows[0].entry_type == EntryType.driving
    assert result.rows[0].end_time is not None


def test_parse_csv_open_ended_row():
    content = (CSV_HEADER + "Иван Петров;;доступность;14.09.2026 06:00;\n").encode("utf-8")
    result = parse_file("export.csv", content)
    assert result.errors == []
    assert result.rows[0].end_time is None
    assert result.rows[0].card_number is None


def test_parse_csv_unknown_activity_type_is_row_error():
    content = (CSV_HEADER + "Иван Петров;;телепортация;14.09.2026 06:00;14.09.2026 07:00\n").encode(
        "utf-8"
    )
    result = parse_file("export.csv", content)
    assert result.rows == []
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2
    assert "телепортация" in result.errors[0].reason


def test_parse_csv_bad_date_is_row_error():
    content = (CSV_HEADER + "Иван Петров;;вождение;не дата;14.09.2026 07:00\n").encode("utf-8")
    result = parse_file("export.csv", content)
    assert result.rows == []
    assert len(result.errors) == 1


def test_parse_csv_end_before_start_is_row_error():
    content = (
        CSV_HEADER + "Иван Петров;;вождение;14.09.2026 10:00;14.09.2026 06:00\n"
    ).encode("utf-8")
    result = parse_file("export.csv", content)
    assert result.rows == []
    assert len(result.errors) == 1


def test_parse_csv_missing_required_column_reports_error():
    content = "ФИО;Тип активности\nИван Петров;вождение\n".encode("utf-8")
    result = parse_file("export.csv", content)
    assert result.rows == []
    assert len(result.errors) == 1
    assert "start_time" in result.errors[0].reason


def test_parse_csv_blank_lines_are_skipped():
    content = (CSV_HEADER + "\n" + "Иван Петров;;вождение;14.09.2026 06:00;14.09.2026 07:00\n").encode(
        "utf-8"
    )
    result = parse_file("export.csv", content)
    assert result.errors == []
    assert len(result.rows) == 1


def test_parse_xlsx_valid_rows():
    wb = Workbook()
    ws = wb.active
    ws.append(["ФИО", "Номер карты", "Тип активности", "Начало", "Окончание"])
    ws.append(["Иван Петров", "123", "вождение", "14.09.2026 06:00", "14.09.2026 10:00"])
    buf = io.BytesIO()
    wb.save(buf)

    result = parse_file("export.xlsx", buf.getvalue())

    assert result.errors == []
    assert len(result.rows) == 1
    assert result.rows[0].entry_type == EntryType.driving


def test_parse_unsupported_extension_raises():
    try:
        parse_file("export.txt", b"data")
        assert False, "expected UnsupportedFileFormatError"
    except UnsupportedFileFormatError:
        pass
