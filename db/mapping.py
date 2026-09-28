"""Translates between the nested Category -> Subcategory -> Parameter -> value
JSON shape (exactly what the form's "Export as JSON" button produces) and the
flat {db_column: python_value} dicts the ORM models need -- in both
directions, driven entirely by db/generated/field_registry.json so there is
exactly one place that knows what a bucket means.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "generated" / "field_registry.json"

_TRUE_STRINGS = {"yes", "true"}


class MappingError(ValueError):
    """Raised with every problem found in a bucket, not just the first."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _load_registry() -> dict[str, dict]:
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


_REGISTRY = _load_registry()
_BY_SCOPE: dict[str, dict[str, dict]] = {}
for _key, _entry in _REGISTRY.items():
    _scope, _rest = _key.split("::", 1)
    _BY_SCOPE.setdefault(_scope, {})[_rest] = _entry


def _unit_basis(rule: dict | None, active_values: dict[str, Any],
                inherited: dict[str, Any]) -> tuple[str | None, str]:
    """Return (liquid/gas basis, the answer that chose it) for a unit rule.

    The field's own-scope answer wins. If it is blank, a fallback answer
    comes from the parent record (a Sand Body's Fluid Type falls back to the
    well's Well type), matching the form. With neither answered the basis is
    unknown; the explicit saved unit still says which stream it measures.
    """
    if not rule:
        return None, ""
    answer = active_values.get(rule["parameter"])
    if answer not in (None, ""):
        return rule["by_answer"].get(str(answer)), f"{rule['parameter']} = {answer!r}"
    fallback = rule.get("fallback")
    answer = inherited.get(fallback["parameter"]) if fallback else None
    if answer not in (None, ""):
        return (fallback["by_answer"].get(str(answer)),
                f"{fallback['parameter']} = {answer!r} ({rule['parameter']} is blank)")
    return None, ""


def _coerce(entry: dict, leaf_key: str, value: Any, errors: list[str],
            active_values: dict[str, Any], inherited: dict[str, Any]) -> dict[str, Any]:
    """Validate an explicit unit, then coerce the associated field value."""
    choices = entry.get("unit_choices", [])
    unit = None
    if isinstance(value, dict):
        if set(value) != {"value", "unit"}:
            errors.append(f"{leaf_key}: expected a value and unit object")
            return {}
        if not choices:
            errors.append(f"{leaf_key}: this field has no unit")
            return {}
        unit = value.get("unit")
        value = value["value"]
    if choices:
        allowed = choices
        basis, reason = _unit_basis(entry.get("unit_basis"), active_values, inherited)
        if basis:
            # Well type / Fluid Type decides liquid vs gas; the other stream's
            # units would describe a different measurement.
            allowed = [choice for choice in choices if choice["group"] == basis]
        if unit in (None, ""):
            unit = allowed[0]["unit"]
        if unit not in [choice["unit"] for choice in allowed]:
            if basis:
                errors.append(f"{leaf_key}: unit {unit!r} does not match {reason}")
            else:
                errors.append(f"{leaf_key}: unit {unit!r} is not allowed")
            return {}
    elif unit not in (None, ""):
        errors.append(f"{leaf_key}: this field has no unit")
        return {}
    measured_entry = entry
    if choices and entry["kind"] == "number":
        # Workbook limits are expressed in its Field unit. Compare a selected
        # SI value against the same physical limits (notably 0°F = -17.78°C).
        source = choices[0]
        target = next(choice for choice in choices if choice["unit"] == unit)
        measured_entry = dict(entry)
        for bound in ("min_value", "max_value"):
            if entry[bound] is None:
                continue
            if source["group"] == target["group"]:
                canonical = float(entry[bound]) * source["scale"] + source["offset"]
                measured_entry[bound] = (canonical - target["offset"]) / target["scale"]
            elif float(entry[bound]) == 0:
                # Zero remains a lower/upper bound in either production basis.
                measured_entry[bound] = 0
            else:
                measured_entry[bound] = None
    columns = _coerce_value(measured_entry, leaf_key, value, errors, active_values)
    if entry.get("unit_column") and unit:
        columns[entry["unit_column"]] = unit
    return columns


def _coerce_value(entry: dict, leaf_key: str, value: Any, errors: list[str],
                  active_values: dict[str, Any]) -> dict[str, Any]:
    """Coerce one bare value after its unit has been checked."""
    if value is None or value == "":
        return {}

    kind = entry["kind"]
    db_type = entry["db_type"]
    columns = entry["db_columns"]

    if kind == "select":
        text_value = str(value)
        options = entry["options"]
        if entry.get("options_by"):
            trigger, choices = next(iter(entry["options_by"].items()))
            options = choices.get(str(active_values.get(trigger, "")), [])
        if text_value not in options and (options or entry.get("options_by")):
            errors.append(f"{leaf_key}: {value!r} is not one of {options}")
            return {}
        if db_type == "Boolean":
            return {columns[0]: text_value.lower() in _TRUE_STRINGS}
        return {columns[0]: text_value}

    if kind == "text":
        text_value = str(value)
        if entry.get("min_length") is not None and len(text_value) < entry["min_length"]:
            errors.append(f"{leaf_key}: {value!r} is shorter than the minimum length {entry['min_length']}")
            return {}
        if entry.get("max_length") is not None and len(text_value) > entry["max_length"]:
            errors.append(f"{leaf_key}: {value!r} is longer than the maximum length {entry['max_length']}")
            return {}
        if entry.get("pattern") and not re.match(entry["pattern"], text_value):
            errors.append(f"{leaf_key}: {value!r} does not match the required format")
            return {}
        return {columns[0]: text_value}

    if kind == "number":
        number = _to_number(value, db_type)
        if number is None:
            errors.append(f"{leaf_key}: {value!r} is not a valid number")
            return {}
        if entry["min_value"] is not None and number < entry["min_value"]:
            errors.append(f"{leaf_key}: {value!r} is below the minimum {entry['min_value']}")
            return {}
        if entry["max_value"] is not None and number > entry["max_value"]:
            errors.append(f"{leaf_key}: {value!r} is above the maximum {entry['max_value']}")
            return {}
        return {columns[0]: number}

    if kind == "date":
        try:
            return {columns[0]: date.fromisoformat(str(value))}
        except ValueError:
            errors.append(f"{leaf_key}: {value!r} is not a YYYY-MM-DD date")
            return {}

    if kind == "multi_number":
        if not isinstance(value, (list, tuple)) or len(value) != len(columns):
            errors.append(f"{leaf_key}: expected {len(columns)} values, got {value!r}")
            return {}
        out: dict[str, Any] = {}
        for column, sub_value in zip(columns, value):
            if sub_value in (None, ""):
                continue
            number = _to_number(sub_value, db_type)
            if number is None:
                errors.append(f"{leaf_key}: {sub_value!r} is not a valid number")
                continue
            out[column] = number
        return out

    errors.append(f"{leaf_key}: unrecognized field kind {kind!r}")
    return {}


def _to_number(value: Any, db_type: str) -> int | Decimal | None:
    try:
        return int(value) if db_type == "Integer" else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _matches(rules: list[dict[str, str]], values: dict[str, Any]) -> bool:
    return any(str(values.get(rule["parameter"], "")) == rule["value"] for rule in rules)


def _visible(entry: dict, values: dict[str, Any]) -> bool:
    """Apply the same OR show/hide rules and parent-section gate as the form."""
    rules = entry.get("visibility", {})
    for prefix in ("subcategory_", ""):
        show = rules.get(prefix + "show", [])
        hide = rules.get(prefix + "hide", [])
        if show and not _matches(show, values):
            return False
        if hide and _matches(hide, values):
            return False
    return True


def _applicable(index: dict[str, dict], bucket: dict) -> tuple[dict[str, bool], dict[str, Any]]:
    """Resolve hidden triggers before deciding which fields are required.

    Form controls disappear and clear when their parent/own rule hides them.
    The submitted bucket should follow the same behavior even if a caller
    constructs JSON by hand. Current workbook triggers have unique names in
    each scope, matching findParamField() in the browser.
    """
    entries = sorted(index.items(), key=lambda pair: pair[1]["row_number"])
    provided = {
        f"{category}::{subcategory}::{parameter}": value
        for category, subcats in (bucket or {}).items()
        for subcategory, params in (subcats or {}).items()
        for parameter, value in (params or {}).items()
    }
    active_values = {}
    for key, entry in entries:
        value = provided.get(key)
        bare = value.get("value") if isinstance(value, dict) else value
        if bare is not None and bare != "":
            active_values.setdefault(entry["parameter"], bare)
    for _ in range(len(entries) + 1):
        changed = False
        for key, entry in entries:
            if not _visible(entry, active_values) and entry["parameter"] in active_values:
                del active_values[entry["parameter"]]
                changed = True
        if not changed:
            break
    return {key: _visible(entry, active_values) for key, entry in entries}, active_values


def parent_answers(bucket: dict[str, dict[str, dict[str, Any]]], scope: str) -> dict[str, Any]:
    """Visible answers in a parent bucket, keyed by Parameter name.

    Passed as flatten_bucket(..., inherited=) for child records whose rules
    fall back to a parent answer. Hidden answers are dropped, as in the form.
    """
    return _applicable(_BY_SCOPE.get(scope, {}), bucket)[1]


def flatten_bucket(bucket: dict[str, dict[str, dict[str, Any]]], scope: str,
                   inherited: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate fields against the workbook registry and flatten DB values.

    A required field only applies when the form would show it. Values sent
    for hidden questions are rejected so hand-built API records cannot carry
    answers that a browser export would have cleared and omitted. `inherited`
    holds parent answers (see parent_answers) for rules that fall back to them.
    """
    inherited = inherited or {}
    index = _BY_SCOPE.get(scope, {})
    visible, active_values = _applicable(index, bucket)
    flat: dict[str, Any] = {}
    errors: list[str] = []
    provided_keys: set[str] = set()

    for category, subcats in (bucket or {}).items():
        for subcategory, params in (subcats or {}).items():
            for parameter, value in (params or {}).items():
                leaf_key = f"{category} / {subcategory} / {parameter}"
                key = f"{category}::{subcategory}::{parameter}"
                entry = index.get(key)
                if entry is None:
                    errors.append(f"{leaf_key}: not a recognized field for this record level")
                    continue
                if not visible[key]:
                    # Unit choices for empty hidden controls are part of a
                    # restorable draft, but hidden answers remain forbidden.
                    bare = value.get("value") if isinstance(value, dict) else value
                    if bare in (None, ""):
                        # Blank hidden fields have no answer, but the selected
                        # unit is still part of the draft state.
                        flat.update(_coerce(entry, leaf_key, value, errors, active_values, inherited))
                        continue
                    errors.append(f"{leaf_key}: hidden by the current form answers")
                    continue
                coerced = _coerce(entry, leaf_key, value, errors, active_values, inherited)
                if any(column in coerced for column in entry["db_columns"]):
                    provided_keys.add(key)
                flat.update(coerced)

    for key, entry in index.items():
        if visible[key] and entry.get("required") and key not in provided_keys:
            errors.append(
                f"{entry['category']} / {entry['subcategory']} / {entry['parameter']}: this field is required"
            )

    if errors:
        raise MappingError(errors)
    return flat


def build_record_out(row_values: dict[str, Any], scope: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Inverse of flatten_bucket: given {db_column: value} for one ORM row,
    regroups into Category -> Subcategory -> Parameter -> value, re-merging
    multi_number sub-columns and re-serializing dates/Decimals/bools back to
    the same JSON-friendly representation the form itself emits.
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for entry in _REGISTRY.values():
        if entry["scope"] != scope:
            continue
        columns = entry["db_columns"]
        if entry["kind"] == "multi_number":
            if all(row_values.get(c) is None for c in columns):
                continue
            value: Any = [_serialize(row_values.get(c)) for c in columns]
        else:
            raw = row_values.get(columns[0])
            if raw is None:
                unit_column = entry.get("unit_column")
                if not unit_column or row_values.get(unit_column) is None:
                    continue
                value = None
            else:
                value = _serialize(raw)
        choices = entry.get("unit_choices", [])
        if choices:
            unit_column = entry.get("unit_column")
            unit = row_values.get(unit_column) if unit_column else choices[0]["unit"]
            value = {"value": value, "unit": unit or choices[0]["unit"]}
        cat_bucket = out.setdefault(entry["category"], {})
        subcat_bucket = cat_bucket.setdefault(entry["subcategory"], {})
        subcat_bucket[entry["parameter"]] = value
    return out


def _serialize(value: Any) -> Any:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Decimal):
        # The form exports numeric values as strings. Keep that representation
        # on API readback so JSON serialization does not pass an exact database
        # Decimal through a binary float and change its digits.
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
