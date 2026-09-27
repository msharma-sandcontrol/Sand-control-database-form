"""dictionary.units: Field/Metric unit cells -> allowed units, per-system
starting units, and the Unit System preset row."""
from __future__ import annotations

import pytest

from dictionary.models import ParamRow
from dictionary.units import (
    FIELD_UNIT_SYSTEM,
    METRIC_UNIT_SYSTEM,
    classify_units,
    default_unit_system,
    find_unit_system_row,
)


def _row(**overrides) -> ParamRow:
    base = dict(
        row_number=1, scope="Well", category="C", subcategory="S", parameter="P",
        input_type="Number", field_unit="", metric_unit="", affected_subcategory="", affected_parameter="",
        data_validation="", tooltip="", user_comment="",
    )
    base.update(overrides)
    return ParamRow(**base)


def _unit_system_row(data_validation: str, **overrides) -> ParamRow:
    return _row(parameter="Unit System", input_type="Dropdown Menu", data_validation=data_validation, **overrides)


def test_different_units_are_selectable():
    units = classify_units(_row(field_unit="ft", metric_unit="m"))
    assert units.options == ["ft", "m"]
    assert units.selectable
    assert units.defaults == {FIELD_UNIT_SYSTEM: "ft", METRIC_UNIT_SYSTEM: "m"}


def test_same_unit_in_both_systems_is_fixed():
    units = classify_units(_row(field_unit="%", metric_unit="%"))
    assert units.options == ["%"]
    assert not units.selectable
    assert units.defaults == {FIELD_UNIT_SYSTEM: "%", METRIC_UNIT_SYSTEM: "%"}


@pytest.mark.parametrize(("field_unit", "metric_unit"), [
    ("pptb or lb/mmscf", "mg/L"),
    ("stb/d/psi or mmscf/d/psi", "Sm3/d/kPa"),
    ("gauge or micron", "micron"),
])
def test_a_cell_is_one_unit_label_taken_verbatim(field_unit, metric_unit):
    # "or" inside a cell is part of the label, not a list of alternatives --
    # a row never offers more than its two cells.
    units = classify_units(_row(field_unit=field_unit, metric_unit=metric_unit))
    assert units.options == [field_unit, metric_unit]
    assert units.defaults == {FIELD_UNIT_SYSTEM: field_unit, METRIC_UNIT_SYSTEM: metric_unit}


def test_unitless_row():
    units = classify_units(_row())
    assert units.options == []
    assert not units.selectable
    assert units.defaults == {}
    assert units.default_for(FIELD_UNIT_SYSTEM) is None


def test_a_missing_cell_falls_back_to_the_unit_the_row_does_have():
    units = classify_units(_row(field_unit="ft", metric_unit=""))
    assert units.defaults == {FIELD_UNIT_SYSTEM: "ft", METRIC_UNIT_SYSTEM: "ft"}


def test_find_unit_system_row():
    row = _unit_system_row('{"List": {"options": ["Field Unit", "Metric Unit"], "default": "Metric Unit"}}')
    assert find_unit_system_row([_row(), row]) is row
    assert default_unit_system([_row(), row]) == METRIC_UNIT_SYSTEM


def test_no_unit_system_row_means_field_units():
    assert find_unit_system_row([_row()]) is None
    assert default_unit_system([_row()]) == FIELD_UNIT_SYSTEM


def test_unit_system_without_default_means_field_units():
    row = _unit_system_row('{"List": {"options": ["Metric Unit", "Field Unit"]}}')
    assert default_unit_system([row]) == FIELD_UNIT_SYSTEM


def test_unit_system_row_only_counts_at_well_scope():
    row = _unit_system_row('{"List": {"options": ["A"]}}', scope="Sand Body {id}")
    assert find_unit_system_row([row]) is None


@pytest.mark.parametrize("data_validation", [
    # Missing closing brace -- the cell doesn't parse, so there are no options.
    '{"List": {"options": ["Field Unit", "Metric Unit"], "default": "Field Unit"}',
    '{"List": {"options": ["Field Unit", "SI Unit"]}}',
    '{"List": {"options": ["Field Unit"]}}',
])
def test_malformed_unit_system_row_fails_loudly(data_validation):
    with pytest.raises(ValueError, match="Unit System"):
        find_unit_system_row([_unit_system_row(data_validation)])


def test_unit_system_default_must_be_an_option():
    row = _unit_system_row('{"List": {"options": ["Field Unit", "Metric Unit"], "default": "Metric"}}')
    with pytest.raises(ValueError, match="default"):
        find_unit_system_row([row])
