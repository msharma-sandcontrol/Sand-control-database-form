"""Units: the `Field Unit` / `Metric Unit` columns and the `Unit System` selector.

Every MasterView row carries two unit cells -- `Field Unit` (oilfield units,
the dictionary's original unit set and still the default) and `Metric Unit`.
Each cell is one unit label, taken verbatim: `pptb or lb/mmscf` is a single
label, not a list to split. So a row offers at most two units -- a fixed one
when both cells hold the same label (`%`, `days`, ...), otherwise a choice
between its field and metric unit.

The Well-scope `Unit System` row is the record-level preset: its options
are exactly the two unit-column headers, so choosing one says which column
every row takes its starting unit from. Values are never converted between
units -- whatever unit a value was entered in travels with it (see
db/mapping.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from dictionary.classify import classify_field
from dictionary.models import WELL_SCOPE, ParamRow

UNIT_SYSTEM_PARAMETER = "Unit System"
# Spelled exactly like the MasterView column headers, so a Unit System option
# names the column its units come from.
FIELD_UNIT_SYSTEM = "Field Unit"
METRIC_UNIT_SYSTEM = "Metric Unit"
UNIT_SYSTEMS = (FIELD_UNIT_SYSTEM, METRIC_UNIT_SYSTEM)


@dataclass
class UnitSpec:
    field_unit: str = ""
    metric_unit: str = ""

    @property
    def options(self) -> list[str]:
        """The units the row accepts: field unit first, a duplicate dropped."""
        return list(dict.fromkeys(u for u in (self.field_unit, self.metric_unit) if u))

    @property
    def selectable(self) -> bool:
        return len(self.options) > 1

    def default_for(self, system: str) -> str | None:
        """`system`'s unit; a row with only one of its two unit cells filled
        falls back to the unit it does have."""
        unit = {FIELD_UNIT_SYSTEM: self.field_unit, METRIC_UNIT_SYSTEM: self.metric_unit}.get(system)
        return unit or (self.options[0] if self.options else None)

    @property
    def defaults(self) -> dict[str, str]:
        """{unit system: starting unit}, or {} for a unitless row."""
        if not self.options:
            return {}
        return {system: self.default_for(system) for system in UNIT_SYSTEMS}


def classify_units(row: ParamRow) -> UnitSpec:
    return UnitSpec(row.field_unit, row.metric_unit)


def is_unit_system_row(row: ParamRow) -> bool:
    return row.scope == WELL_SCOPE and row.parameter == UNIT_SYSTEM_PARAMETER


def find_unit_system_row(rows: list[ParamRow]) -> ParamRow | None:
    """The `Unit System` row, or None if the dictionary has none (every row
    then just starts in field units). Matched by exact Parameter name, like
    the form's other special rows. Raises ValueError if the row exists but
    isn't a dropdown of exactly the unit systems -- nothing else could say
    which unit column an option stands for.
    """
    row = next((r for r in rows if is_unit_system_row(r)), None)
    if row is None:
        return None
    spec = classify_field(row)
    if spec.kind != "select" or sorted(spec.options) != sorted(UNIT_SYSTEMS):
        raise ValueError(
            f"MasterView row {row.row_number} ({UNIT_SYSTEM_PARAMETER!r}) must be a dropdown whose options are "
            f"exactly {list(UNIT_SYSTEMS)}, got {spec.options} from Data Validation {row.data_validation!r} "
            f"(check that the cell parses, e.g. that its braces are balanced)"
        )
    if spec.default is not None and spec.default not in spec.options:
        raise ValueError(
            f"MasterView row {row.row_number} ({UNIT_SYSTEM_PARAMETER!r}): default {spec.default!r} "
            f"is not one of its options {spec.options}"
        )
    return row


def default_unit_system(rows: list[ParamRow]) -> str:
    """The unit system a new record starts in: the `Unit System` row's
    `default`, else field units -- every value collected before the Metric
    Unit column existed was in field units."""
    row = find_unit_system_row(rows)
    default = classify_field(row).default if row is not None else None
    return default or FIELD_UNIT_SYSTEM
