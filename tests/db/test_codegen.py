"""Runs db.codegen against the real MASTER.xlsx and checks (a) it completes
without a naming collision or oversized identifier, and (b) what it
produces matches what's already committed under db/generated/ -- the same
drift check CI runs, so a dictionary edit that wasn't followed by
`python -m db.codegen` fails locally too, not just in CI.
"""
from __future__ import annotations

import json
from pathlib import Path

from db import codegen

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = REPO_ROOT / "db" / "generated"
GENERATED_FILES = [
    "well_columns.py",
    "completion_interval_columns.py",
    "sand_body_columns.py",
    "field_registry.json",
]


def test_codegen_runs_without_error(tmp_path, monkeypatch):
    # Into a scratch directory: writing the real db/generated/ here would
    # also make the drift check below compare fresh output against itself.
    monkeypatch.setattr(codegen, "GENERATED_DIR", tmp_path)
    per_table = codegen.generate()
    assert set(per_table.keys()) == {"well", "completion_interval", "sand_body"}
    assert len(per_table["well"]) > 0
    assert len(per_table["completion_interval"]) > 0
    assert len(per_table["sand_body"]) > 0


def test_generated_output_matches_committed_files(tmp_path, monkeypatch):
    # Regenerate into a scratch directory rather than overwriting the real
    # db/generated/ as a side effect of running the test suite.
    monkeypatch.setattr(codegen, "GENERATED_DIR", tmp_path)
    codegen.generate()

    for name in GENERATED_FILES:
        committed = (GENERATED_DIR / name).read_text(encoding="utf-8")
        fresh = (tmp_path / name).read_text(encoding="utf-8")
        assert fresh == committed, f"{name} is stale -- run `python -m db.codegen` and commit the result"


def test_field_registry_has_one_entry_per_dictionary_row():
    from dictionary import load_dictionary

    registry = json.loads((GENERATED_DIR / "field_registry.json").read_text(encoding="utf-8"))
    rows = load_dictionary(codegen.MASTER_XLSX)
    assert len(registry) == len(rows)


def test_multi_number_fields_expand_to_multiple_columns():
    # "Mud PSD D10/D25/D40/D50/D75/D90"'s Parameter name carries a trailing
    # D-labeled suffix, so its sub-labels are derived from that suffix (see
    # dictionary.parsing._derive_multi_labels) rather than falling back to
    # the generic "Value 1", "Value 2", ... convention.
    registry = json.loads((GENERATED_DIR / "field_registry.json").read_text(encoding="utf-8"))
    entry = registry["completion_interval::Completion::OH Drilling Details::Mud PSD D10/D25/D40/D50/D75/D90"]
    assert entry["db_columns"] == [
        "mud_psd_d10", "mud_psd_d25", "mud_psd_d40", "mud_psd_d50", "mud_psd_d75", "mud_psd_d90",
    ]
    assert entry["db_type"] == "Numeric"


def _registry() -> dict:
    return json.loads((GENERATED_DIR / "field_registry.json").read_text(encoding="utf-8"))


def test_selectable_unit_gets_a_unit_column():
    entry = _registry()["well::Well Specific::Well & Field Identification::Water depth"]
    assert entry["unit_options"] == ["ft", "m"]
    assert entry["default_units"] == {"Field Unit": "ft", "Metric Unit": "m"}
    assert entry["unit_column"] == "water_depth_unit"


def test_fixed_unit_has_no_unit_column():
    entry = _registry()["well::Well Specific::Production Performance History::Peak water cut"]
    assert entry["unit_options"] == ["%"]
    assert entry["unit_column"] is None


def test_unitless_field_has_no_unit_metadata():
    entry = _registry()["well::Well Specific::Well & Field Identification::Well type"]
    assert entry["unit_options"] == []
    assert entry["default_units"] == {}
    assert entry["unit_column"] is None


def test_unit_columns_are_text_columns_of_their_table():
    import db.models  # noqa: F401  (populates Base.metadata as a side effect)
    from db.base import Base

    entries = [e for e in _registry().values() if e["unit_column"]]
    assert entries
    for entry in entries:
        column = Base.metadata.tables[entry["table"]].columns[entry["unit_column"]]
        assert type(column.type).__name__ == "Text"
        assert column.nullable


def test_unit_system_entry_is_flagged():
    flagged = [e for e in _registry().values() if e["is_unit_system"]]
    assert [(e["scope"], e["parameter"], e["db_columns"]) for e in flagged] == [
        ("well", "Unit System", ["unit_system"]),
    ]
    assert flagged[0]["default"] == "Field Unit"
