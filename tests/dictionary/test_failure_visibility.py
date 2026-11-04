"""Protect the representative's Yes/No field sets after merging the sections.

The published row lists predate deletion of old row 18, so every affected
row number after severity is one lower in the current workbook. Deleting
Well start-up date (old row 38) lowered every row after it by one more, and
the November round (Well name removed, two multilateral rows added, both TD
rows moved to the Lateral level) lowered this section by one more again.
"""
from __future__ import annotations

from db.mapping import _REGISTRY

YES_ONLY = {16} | set(range(17, 24)) | set(range(31, 36)) | set(range(39, 45))
SHARED = set(range(27, 31)) | set(range(36, 39)) | set(range(45, 56))


def test_failure_confirmation_only_controls_its_extra_questions():
    well = [entry for entry in _REGISTRY.values() if entry["scope"] == "well"]
    merged = [entry for entry in well if entry["subcategory"] == "Sand Production & Well Performance"]
    assert {entry["row_number"] for entry in merged if any(
        rule["parameter"] == "Sand Control Failure" for rule in entry.get("visibility", {}).get("show", [])
    )} == YES_ONLY
    for entry in merged:
        visibility = entry.get("visibility", {})
        assert not visibility.get("subcategory_show")
        assert not visibility.get("subcategory_hide")
        if entry["row_number"] in SHARED:
            assert not any(rule["parameter"] == "Sand Control Failure" for rule in visibility.get("show", []))


def test_severity_is_one_required_yes_only_field_with_type_specific_choices():
    severity = [entry for entry in _REGISTRY.values() if entry["parameter"] == "Severity of sand production"]
    assert len(severity) == 1
    entry = severity[0]
    assert entry["required"]
    assert entry["visibility"]["show"] == [{"parameter": "Sand Control Failure", "value": "Yes"}]
    assert "lb/MMSCF" not in " ".join(entry["options_by"]["Well type"]["Oil Producer"])


def test_sand_rates_still_depend_on_measurable_quantification():
    rows = [entry for entry in _REGISTRY.values() if 24 <= entry["row_number"] <= 26]
    assert len(rows) == 3
    for entry in rows:
        assert entry["visibility"]["show"] == [
            {"parameter": "Sand rate quantification", "value": "Measurable"},
        ]
