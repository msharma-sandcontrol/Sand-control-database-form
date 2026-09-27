"""Turns dictionary Parameter names into valid, stable Postgres column names."""
from __future__ import annotations

import re

from dictionary import MULTI_LABEL_SUFFIX_RE

# Postgres truncates identifiers silently past this length -- codegen refuses
# to emit anything longer so a collision can never be hidden by truncation.
MAX_IDENTIFIER_LENGTH = 63

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """'Well TD, MD' -> 'well_td_md'; 'k.h from PTA' -> 'k_h_from_pta'."""
    slug = _NON_ALNUM_RE.sub("_", text.strip().lower()).strip("_")
    if not slug:
        raise ValueError(f"{text!r} slugifies to an empty string")
    return slug


def strip_multi_suffix(parameter: str) -> str:
    """'Particle Size Distribution D10/D25/.../D90' -> 'Particle Size Distribution'.

    Mirrors the suffix `dictionary.parsing.MULTI_LABEL_SUFFIX_RE` matches when
    deriving multi-number sub-field labels from the parameter name itself, so
    the generated base column name doesn't repeat the label text.
    """
    m = MULTI_LABEL_SUFFIX_RE.search(parameter)
    if not m:
        return parameter
    return parameter[: m.start()].strip()


def derive_column_names(parameter: str, kind: str, multi_labels: list[str]) -> list[str]:
    """The DB column name(s) a dictionary row maps to.

    A plain field maps to one column named after the Parameter. A
    multi_number field expands into one column per sub-label, prefixed by
    the parameter's own (suffix-stripped) slug, e.g. "Mud PSD" + ["D10",
    "D50", "D90"] -> ["mud_psd_d10", "mud_psd_d50", "mud_psd_d90"]. A row
    with selectable units also gets a unit column -- see
    derive_unit_column_name.
    """
    if kind == "multi_number":
        base = slugify(strip_multi_suffix(parameter))
        names = [f"{base}_{slugify(label)}" for label in multi_labels]
    else:
        names = [slugify(parameter)]
    for name in names:
        _check_identifier_length(name, parameter)
    return names


def derive_unit_column_name(parameter: str, kind: str) -> str:
    """The column recording which unit a value was entered in, for a row that
    offers a choice of units: "Water depth" -> "water_depth_unit". A
    multi_number row has one unit for all of its sub-values, so it gets one
    unit column named after its (suffix-stripped) base slug.
    """
    base = slugify(strip_multi_suffix(parameter)) if kind == "multi_number" else slugify(parameter)
    name = f"{base}_unit"
    _check_identifier_length(name, parameter)
    return name


def _check_identifier_length(name: str, parameter: str) -> None:
    if len(name.encode("utf-8")) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"derived column name {name!r} ({len(name)} bytes) exceeds Postgres's "
            f"{MAX_IDENTIFIER_LENGTH}-byte identifier limit (from Parameter {parameter!r})"
        )
