"""Shared parser for the Sand Control Failure Data Dictionary (MASTER.xlsx).

This package is the single place that knows how to read MASTER.xlsx and
interpret its DSL (Data Validation / Affected Subcategory / Affected
Parameter cells) and its Field Unit / Metric Unit columns. It has no
knowledge of HTML or SQL -- form/generate_form.py
and db/codegen.py both import from here so the dictionary stays the one
source of truth for what a cell means, instead of each consumer maintaining
its own interpretation.
"""
from dictionary.classify import classify_field
from dictionary.grouping import group_by_category_subcategory
from dictionary.loader import SHEET_NAME, load_dictionary
from dictionary.models import (
    COMPLETION_SCOPE,
    SAND_BODY_SCOPE,
    WELL_SCOPE,
    FieldSpec,
    ParamRow,
)
from dictionary.parsing import (
    MULTI_LABEL_SUFFIX_RE,
    parse_affected_cell,
    parse_dropdown_options,
    parse_multi_number,
    parse_validation_cell,
    safe_literal,
)
from dictionary.units import (
    FIELD_UNIT_SYSTEM,
    METRIC_UNIT_SYSTEM,
    UNIT_SYSTEM_PARAMETER,
    UNIT_SYSTEMS,
    UnitSpec,
    classify_units,
    default_unit_system,
    find_unit_system_row,
    is_unit_system_row,
)

__all__ = [
    "COMPLETION_SCOPE",
    "FIELD_UNIT_SYSTEM",
    "METRIC_UNIT_SYSTEM",
    "MULTI_LABEL_SUFFIX_RE",
    "SAND_BODY_SCOPE",
    "SHEET_NAME",
    "UNIT_SYSTEMS",
    "UNIT_SYSTEM_PARAMETER",
    "WELL_SCOPE",
    "FieldSpec",
    "ParamRow",
    "UnitSpec",
    "classify_field",
    "classify_units",
    "default_unit_system",
    "find_unit_system_row",
    "group_by_category_subcategory",
    "is_unit_system_row",
    "load_dictionary",
    "parse_affected_cell",
    "parse_dropdown_options",
    "parse_multi_number",
    "parse_validation_cell",
    "safe_literal",
]
