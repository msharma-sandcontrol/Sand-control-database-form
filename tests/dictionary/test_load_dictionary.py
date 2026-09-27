"""Loads the REAL MASTER.xlsx and asserts structural invariants the rest of
the pipeline (form generator, db codegen) depends on. If a future
dictionary edit breaks one of these, this test is meant to fail loudly here
rather than let a downstream generator silently misbehave.
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from dictionary import (
    COMPLETION_SCOPE,
    FIELD_UNIT_SYSTEM,
    SAND_BODY_SCOPE,
    UNIT_SYSTEMS,
    WELL_SCOPE,
    classify_field,
    default_unit_system,
    find_unit_system_row,
    load_dictionary,
)
from dictionary.loader import COLUMNS, SHEET_NAME

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_XLSX = REPO_ROOT / "MASTER.xlsx"


def _write_sheet(path: Path, header: list[str], rows: list[list]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(header)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_columns_are_found_by_header_not_position(tmp_path):
    header = list(reversed(COLUMNS))  # every column moved
    values = {
        "Row Number": 7, "Scope": "Well", "Category": "C", "Subcategory": "S", "Parameter": "Water depth",
        "Input Type": "Number", "Field Unit": "ft", "Metric Unit": "m", "Data Validation": '{"Decimal"}',
    }
    path = _write_sheet(tmp_path / "d.xlsx", header, [[values.get(h) for h in header]])
    (row,) = load_dictionary(path)
    assert (row.row_number, row.parameter, row.field_unit, row.metric_unit) == (7, "Water depth", "ft", "m")
    assert row.data_validation == '{"Decimal"}'
    assert row.affected_parameter == ""


def test_missing_column_fails_loudly(tmp_path):
    header = [h for h in COLUMNS if h != "Metric Unit"]
    path = _write_sheet(tmp_path / "d.xlsx", header, [])
    with pytest.raises(SystemExit, match="Metric Unit"):
        load_dictionary(path)


def test_master_xlsx_exists():
    assert MASTER_XLSX.exists(), "MASTER.xlsx must exist at the repo root"


def test_loads_a_substantial_number_of_rows():
    rows = load_dictionary(MASTER_XLSX)
    assert len(rows) > 100


def test_every_row_has_required_fields():
    rows = load_dictionary(MASTER_XLSX)
    for row in rows:
        assert row.parameter, f"blank Parameter (category={row.category!r})"
        assert row.scope in (WELL_SCOPE, COMPLETION_SCOPE, SAND_BODY_SCOPE), (
            f"unexpected Scope {row.scope!r} on parameter {row.parameter!r}"
        )
        assert row.category, f"blank Category on parameter {row.parameter!r}"
        assert row.subcategory, f"blank Subcategory on parameter {row.parameter!r}"
        assert row.input_type, f"blank Input Type on parameter {row.parameter!r}"


def test_tooltip_is_optional_and_loads_as_blank_when_absent():
    # A Tooltip is a nice-to-have, not a requirement -- a row without one
    # loads with tooltip="" and the form simply omits its "?" icon
    # (see form/generate_form.py:render_field_row's `if row.tooltip` check).
    rows = load_dictionary(MASTER_XLSX)
    for r in rows:
        assert isinstance(r.tooltip, str)


def test_no_duplicate_parameter_within_same_category_subcategory():
    rows = load_dictionary(MASTER_XLSX)
    seen = set()
    dupes = []
    for r in rows:
        key = (r.category, r.subcategory, r.parameter)
        if key in seen:
            dupes.append(key)
        seen.add(key)
    assert not dupes, f"duplicate (Category, Subcategory, Parameter) rows: {dupes}"


def test_no_leading_or_trailing_whitespace():
    rows = load_dictionary(MASTER_XLSX)
    for r in rows:
        for field_name in ("category", "subcategory", "parameter", "scope"):
            value = getattr(r, field_name)
            assert value == value.strip(), f"{field_name} has leading/trailing whitespace: {value!r}"


def test_unit_system_row_is_a_valid_preset():
    # find_unit_system_row raises if the row's Data Validation doesn't parse
    # to exactly the unit systems (e.g. a cell missing its closing brace).
    rows = load_dictionary(MASTER_XLSX)
    row = find_unit_system_row(rows)
    assert row is not None, "MASTER.xlsx has no Well-scope 'Unit System' row"
    assert sorted(classify_field(row).options) == sorted(UNIT_SYSTEMS)
    assert default_unit_system(rows) == FIELD_UNIT_SYSTEM


def test_every_select_default_is_one_of_its_options():
    for r in load_dictionary(MASTER_XLSX):
        spec = classify_field(r)
        if spec.default is not None:
            assert spec.default in spec.options, f"row {r.row_number}: default {spec.default!r} not in {spec.options}"


def test_unit_cells_are_filled_in_pairs():
    # A row with only one of its two unit cells filled would show the same
    # unit whichever system is chosen -- almost certainly a missed cell.
    for r in load_dictionary(MASTER_XLSX):
        assert bool(r.field_unit) == bool(r.metric_unit), (
            f"row {r.row_number} ({r.parameter!r}): Field Unit {r.field_unit!r} vs Metric Unit {r.metric_unit!r}"
        )
