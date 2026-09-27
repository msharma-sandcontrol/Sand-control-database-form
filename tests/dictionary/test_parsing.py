"""Unit tests for dictionary.parsing against representative cell strings
(not the real MASTER.xlsx -- see test_load_dictionary.py for that)."""
from __future__ import annotations

from dictionary.parsing import (
    parse_affected_cell,
    parse_dropdown_options,
    parse_multi_number,
    parse_validation_cell,
    safe_literal,
)


def test_safe_literal_valid():
    assert safe_literal('{"A", "B"}') == {"A", "B"}
    assert safe_literal('{"min": 1, "max": 10}') == {"min": 1, "max": 10}
    assert safe_literal("None") is None


def test_safe_literal_tolerates_lowercase_json_booleans_and_null():
    assert safe_literal('{"min": 1, "required": true}') == {"min": 1, "required": True}
    assert safe_literal('{"required": false}') == {"required": False}
    assert safe_literal('{"min": null}') == {"min": None}


def test_safe_literal_invalid_returns_none():
    assert safe_literal("not a literal {") is None
    assert safe_literal("") is None
    assert safe_literal(None) is None


def _spec(type_name: str, **modifiers) -> dict:
    """A parsed spec dict: every key present, unset modifiers at their defaults."""
    spec = {
        "type": type_name, "options": None, "min": None, "max": None, "required": False, "pattern": None,
        "length": None, "default": None,
    }
    spec.update(modifiers)
    return spec


def test_parse_validation_cell_bare_type():
    assert parse_validation_cell('{"Decimal"}') == _spec("Decimal")


def test_parse_validation_cell_with_modifiers():
    assert parse_validation_cell('{"Whole number": {"min": 1, "max": 10}}') == _spec("Whole number", min=1, max=10)


def test_parse_validation_cell_required():
    spec = parse_validation_cell('{"Whole number": {"required": True, "min": 0}}')
    assert spec["required"] is True
    assert spec["min"] == 0


def test_parse_validation_cell_list():
    assert parse_validation_cell('{"List": ["Zebra", "Apple", "Mango"]}') == _spec(
        "List", options=["Zebra", "Apple", "Mango"],
    )


def test_parse_validation_cell_list_options_nested():
    # Current MASTER.xlsx shape -- options live under "options" so other
    # modifiers (e.g. "required") can sit alongside them.
    assert parse_validation_cell('{"List": {"options": ["Zebra", "Apple"], "required": True}}') == _spec(
        "List", options=["Zebra", "Apple"], required=True,
    )


def test_parse_validation_cell_list_default():
    # The Unit System row's shape: a pre-selected option alongside the list.
    assert parse_validation_cell(
        '{"List": {"options": ["Field Unit", "Metric Unit"], "default": "Field Unit"}}'
    ) == _spec("List", options=["Field Unit", "Metric Unit"], default="Field Unit")


def test_parse_validation_cell_unbalanced_braces_does_not_parse():
    # A cell missing its closing brace must not be half-read -- callers see
    # None and the real-sheet tests flag the row.
    assert parse_validation_cell('{"List": {"options": ["Field Unit", "Metric Unit"], "default": "Field Unit"}') is None


def test_parse_validation_cell_text_with_length_and_pattern():
    # Current MASTER.xlsx shape for a length-constrained Text field, e.g.
    # the anonymized well identification number.
    assert parse_validation_cell('{"Text": {"length": 7, "pattern": "alphanumeric", "required": True}}') == _spec(
        "Text", required=True, pattern="alphanumeric", length=7,
    )


def test_parse_validation_cell_any_value():
    assert parse_validation_cell('{"Any Value": {}}') == _spec("Any Value")


def test_parse_validation_cell_blank():
    assert parse_validation_cell("") is None
    assert parse_validation_cell(None) is None


def test_parse_validation_cell_multi_number_malformed_bracket_shape():
    # The real sheet's multi-number cells look like this: not valid literal
    # syntax on their own, recovered segment by segment.
    specs = parse_validation_cell('{["Decimal": {"min": 0}, "Decimal": {"min": 0}, "Decimal": {"min": 0}]}')
    assert specs == [_spec("Decimal", min=0)] * 3


def test_parse_validation_cell_multi_number_well_formed_list_shape():
    # A cleanly-written list-of-specs is supported too, not just the
    # malformed wrapper the current sheet happens to use.
    specs = parse_validation_cell('[{"Decimal": {"min": 0}}, {"Whole number": {"min": 1}}]')
    assert specs == [_spec("Decimal", min=0), _spec("Whole number", min=1)]


def test_parse_dropdown_options_preserves_source_order():
    assert parse_dropdown_options('{"List": ["Zebra", "Apple", "Mango"]}') == ["Zebra", "Apple", "Mango"]


def test_parse_dropdown_options_empty():
    assert parse_dropdown_options("") == []
    assert parse_dropdown_options(None) == []
    assert parse_dropdown_options('{"Decimal"}') == []


def test_parse_multi_number_labels_from_parameter_suffix():
    raw = '{[' + ", ".join(['"Decimal": {"min": 0}'] * 6) + ']}'
    labels, specs = parse_multi_number(raw, "PSD D10/D25/D40/D50/D75/D90")
    assert labels == ["D10", "D25", "D40", "D50", "D75", "D90"]
    assert len(specs) == 6
    assert all(s["min"] == 0 for s in specs)


def test_parse_multi_number_generic_fallback_when_suffix_count_mismatched():
    raw = '{["Decimal": {}, "Decimal": {}]}'
    labels, _specs = parse_multi_number(raw, "Mud PSD D10/D50/D90")
    assert labels == ["Value 1", "Value 2"]


def test_parse_multi_number_generic_fallback():
    raw = '{["Decimal": {}, "Decimal": {}]}'
    labels, _specs = parse_multi_number(raw, "Some Pair")
    assert labels == ["Value 1", "Value 2"]


def test_parse_multi_number_not_a_multi_field():
    assert parse_multi_number('{"Decimal": {"min": 0}}', "Water depth") is None
    assert parse_multi_number("", "Anything") is None


def test_parse_affected_cell_show_convention():
    rules = parse_affected_cell('{"Yes": {"Failure Details & Performance Impact"}}')
    assert rules == [("Yes", "Failure Details & Performance Impact", False)]


def test_parse_affected_cell_hide_convention():
    rules = parse_affected_cell('{"Onshore": {"Water depth": False, "Tree type": False}}')
    assert set(rules) == {("Onshore", "Water depth", True), ("Onshore", "Tree type", True)}


def test_parse_affected_cell_multiple_triggers():
    rules = parse_affected_cell('{"Open Hole": {"Open Hole Details"}, "Cased Hole": {"Cased Hole Details"}}')
    assert set(rules) == {
        ("Open Hole", "Open Hole Details", False),
        ("Cased Hole", "Cased Hole Details", False),
    }


def test_parse_affected_cell_empty():
    assert parse_affected_cell("") == []
    assert parse_affected_cell(None) == []
