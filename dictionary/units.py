"""Field/SI unit choices and reversible numeric conversions for MASTER.xlsx.

All scales map a displayed value to a canonical SI value within its measurement
basis: canonical = value * scale + offset. The same physical basis must be kept
when converting a populated field. Standard gas volumes use 60 F/14.73 psia
on *both* sides; see docs/unit_conversion_review.md for sources and review.
"""
from __future__ import annotations

from dictionary.models import ParamRow

FT = 0.3048
INCH = 0.0254
LB = 0.45359237
GALLON = 0.003785411784
BARREL = 42 * GALLON
SCF = FT**3
PSI = LB * 9.80665 / INCH**2

# Field label -> (SI label, Field-to-SI scale, offset). Unchanged practical
# units remain fixed; this includes percent, days, degrees, litres, microns,
# and millidarcies. A missing label fails loudly during form/code generation.
PAIRS = {
    "%": ("%", 1, 0),
    "L": ("L", 1, 0),
    "bpm": ("L/s", BARREL * 1000 / 60, 0),
    "cP": ("Pa·s", 0.001, 0),
    "days": ("days", 1, 0),
    "degF": ("°C", 5 / 9, -32 * 5 / 9),
    "degrees": ("degrees", 1, 0),
    "ft": ("m", FT, 0),
    "inch": ("cm", 2.54, 0),
    "lb/bbl": ("kg/m³", LB / BARREL, 0),
    "lbs/ft": ("kg/m", LB / FT, 0),
    "md": ("md", 1, 0),
    "md-ft": ("md-m", FT, 0),
    "micron": ("micron", 1, 0),
    "microsips": ("1/Pa", 1e-6 / PSI, 0),
    "mmscf/d": ("Sm³/d", 1e6 * SCF, 0),
    "ppa": ("kg/m³ clean fluid", LB / GALLON, 0),
    "ppg": ("g/cm³", LB / GALLON / 1000, 0),
    "rb/STB": ("m³ reservoir/m³ stock tank", 1, 0),
    "psi": ("kPa", PSI / 1000, 0),
    "scf/stb": ("Sm³/Sm³", SCF / BARREL, 0),
    "shots/ft": ("shots/m", 1 / FT, 0),
    "stb/d": ("Sm³/d", BARREL, 0),
}


def _choice(unit: str, system: str, group: str, scale: float, offset: float = 0) -> dict:
    return {"unit": unit, "system": system, "group": group, "scale": scale, "offset": offset}


def choices_for(row: ParamRow) -> list[dict]:
    """The actual selectable units for a dictionary row, Field first."""
    label = row.unit
    if not label:
        return []
    if label == "pptb or lb/mmscf":
        return [
            _choice("pptb", "Field", "liquid", LB * 1e6 / (1000 * BARREL * 1000)),
            _choice("lb/MMSCF", "Field", "gas", LB * 1e6 / (1e6 * SCF)),
            _choice("mg/L liquid", "SI", "liquid", 1),
            _choice("mg/Sm³ gas", "SI", "gas", 1),
        ]
    if label == "stb/d/psi or mmscf/d/psi":
        return [
            _choice("stb/d/psi", "Field", "liquid", BARREL / (PSI / 1000)),
            _choice("MMSCF/d/psi", "Field", "gas", 1e6 * SCF / (PSI / 1000)),
            _choice("Sm³ liquid/d/kPa", "SI", "liquid", 1),
            _choice("Sm³ gas/d/kPa", "SI", "gas", 1),
        ]
    if label == "res ft³/scf or rb/scf":
        return [
            _choice("res ft³/scf", "Field", "gas_fvf", 1),
            _choice("rb/scf", "Field", "gas_fvf", BARREL / SCF),
            _choice("m³ reservoir/Sm³ gas", "SI", "gas_fvf", 1),
        ]
    if label == "gauge or micron":
        return [
            _choice("screen gauge", "Field", "opening", 25.4),
            _choice("micron", "both", "opening", 1),
        ]
    if label == "ppg" and row.parameter == "Frac gradient":
        return [
            _choice("ppg", "Field", "gradient", LB / GALLON * 9.80665 / 1000),
            _choice("kPa/m", "SI", "gradient", 1),
        ]
    if label not in PAIRS:
        raise ValueError(f"No conversion mapping for row {row.row_number}: {label!r}")
    si, scale, offset = PAIRS[label]
    if label == si:
        return [_choice(label, "both", "default", 1)]
    return [_choice(label, "Field", "default", scale, offset), _choice(si, "SI", "default", 1)]


# A liquid/gas measurement takes its basis from an answer elsewhere in the
# record rather than from a per-field choice. Only Field/SI within that basis
# is selectable, so a number is never silently reinterpreted as the other
# production stream. The keys must match the driver's workbook options.
BASIS_DRIVERS = {
    "Well type": {
        "Oil Producer": "liquid",
        "Gas Producer": "gas",
        "Gas Condensate Producer": "gas",
    },
    "Fluid Type": {"Oil": "liquid", "Condensate": "gas", "Wet Gas": "gas", "Dry Gas": "gas"},
}


def basis_driver(row: ParamRow) -> str | None:
    """The answer that selects liquid or gas units for this row, if any.

    Well and Completion Interval rows follow Well type. A Sand Body row follows
    its own Fluid Type; the form falls back to Well type while that is blank.
    """
    groups = {choice["group"] for choice in choices_for(row)}
    if not {"liquid", "gas"} <= groups:
        return None
    return "Fluid Type" if row.scope.startswith("Sand Body") else "Well type"


def basis_rule(row: ParamRow) -> dict | None:
    """The registry form of basis_driver(), including the Well type fallback.

    A Sand Body answer that is blank inherits the parent well's Well type, so
    the API needs the fallback spelled out to match the form. Other drivers
    have none because Well type is the top of the chain.
    """
    driver = basis_driver(row)
    if not driver:
        return None
    rule = {"parameter": driver, "by_answer": BASIS_DRIVERS[driver]}
    if driver != "Well type":
        rule["fallback"] = {"parameter": "Well type", "by_answer": BASIS_DRIVERS["Well type"]}
    return rule


def option_names(row: ParamRow) -> list[str]:
    return [choice["unit"] for choice in choices_for(row)]
