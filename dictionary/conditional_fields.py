"""Expand one workbook row into its conditional oil/gas FVF alternatives.

The workbook's row 145 retains its original Oil Bo definition. Fluid Type's
Affected Parameter rule names a Gas Bg alternative at the same displayed row
position. Expanding it here gives the form, logic explorer, and API registry
identical field keys and visibility rules without renumbering later rows.
"""
from __future__ import annotations

from dataclasses import replace

from dictionary.models import SAND_BODY_SCOPE, ParamRow

OIL_FVF = "Oil Formation Volume Factor (Bo) at downhole conditions"
GAS_FVF = "Gas Formation Volume Factor (Bg) at downhole conditions"
GAS_FVF_UNIT = "res ft³/scf or rb/scf"
GAS_FVF_TOOLTIP = (
    "Reservoir gas volume per standard gas volume at the specified downhole "
    "pressure and temperature. Standard gas uses 60°F and 14.73 psia."
)


def expand_conditional_rows(rows: list[ParamRow]) -> list[ParamRow]:
    """Return workbook rows with Gas Bg immediately after Oil Bo, both row 145."""
    expanded = []
    found = False
    for row in rows:
        expanded.append(row)
        if row.parameter == OIL_FVF and row.scope == SAND_BODY_SCOPE:
            if found:
                raise ValueError("Oil FVF row occurs more than once")
            found = True
            expanded.append(replace(
                row,
                parameter=GAS_FVF,
                unit=GAS_FVF_UNIT,
                tooltip=GAS_FVF_TOOLTIP,
                affected_parameter="",
                affected_subcategory="",
            ))
    if not found:
        raise ValueError("Oil FVF row is missing from the workbook")
    return expanded
