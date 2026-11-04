"""The record's repeatable levels and the counter field that sizes each one.

    Well
     └── Lateral {id}              sized by Well "Number of laterals"
          └── Completion Interval  sized by Lateral "Number of Completion Intervals"
               └── Sand Body       sized by Completion Interval "Number of sand bodies"

Each counter is the only way to change how many blocks its level has: the
form's Apply button adds or removes blocks to match it, and the API rejects
a record whose counts disagree with its blocks. A well that is not
multilateral has exactly one lateral (its main bore) and no lateral counter.

The workbook counter's `max` is the cap for that level, shared by the form
and the API. Counters are matched by exact Parameter name, so renaming one
in MASTER.xlsx fails generation loudly instead of silently dropping the cap.
"""
from __future__ import annotations

from dataclasses import dataclass

from dictionary.classify import classify_field
from dictionary.models import COMPLETION_SCOPE, LATERAL_SCOPE, SAND_BODY_SCOPE, WELL_SCOPE, ParamRow

MULTILATERAL_PARAMETER = "Is this a Multilateral Well?"


@dataclass(frozen=True)
class Level:
    key: str             # registry key of the repeated level
    scope: str           # its Scope literal in MASTER.xlsx
    parent: str          # registry key of the level holding its counter
    counter_scope: str   # that parent's Scope literal
    counter: str         # the counter's Parameter name


LEVELS = (
    Level("lateral", LATERAL_SCOPE, "well", WELL_SCOPE, "Number of laterals"),
    Level("completion_interval", COMPLETION_SCOPE, "lateral", LATERAL_SCOPE, "Number of Completion Intervals"),
    Level("sand_body", SAND_BODY_SCOPE, "completion_interval", COMPLETION_SCOPE, "Number of sand bodies"),
)


def level_limits(rows: list[ParamRow]) -> dict[str, int]:
    """{level key: maximum blocks}, read from each counter's workbook max."""
    limits = {}
    for level in LEVELS:
        matches = [r for r in rows if r.scope == level.counter_scope and r.parameter == level.counter]
        if len(matches) != 1:
            raise ValueError(f"expected one {level.counter!r} row at {level.counter_scope!r} scope")
        spec = classify_field(matches[0])
        if spec.max_value is None or spec.step != 1:
            raise ValueError(f"{level.counter!r} must be a whole number with a max")
        limits[level.key] = int(spec.max_value)
    return limits
