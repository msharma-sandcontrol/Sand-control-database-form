"""Fixed-format ID masks, e.g. "AAA-I-#####" for XOM-I-00001.

A mask is written in a Text row's Data Validation cell as
`{"Text": {"mask": "AAA-I-#####"}}`. In a mask, `A` stands for one capital
letter and `#` for one digit; every other character is fixed text that the
form shows between the boxes and stores as part of the value. The form draws
one box per run of `A`s or `#`s, and the API checks the same format through
the regex derived here, so both read the one workbook cell.
"""
from __future__ import annotations

import re

SLOT_CLASSES = {"A": "[A-Z]", "#": "[0-9]"}
# Escape only regex syntax characters. re.escape() would also escape "-",
# and browsers reject "\\-" in an HTML pattern (compiled in Unicode mode).
_REGEX_SYNTAX = set("\\^$.|?*+()[]{}/")


def _escape(text: str) -> str:
    return "".join("\\" + ch if ch in _REGEX_SYNTAX else ch for ch in text)


def mask_tokens(mask: str) -> list[dict]:
    """'AAA-I-#####' -> [slot A x3, literal '-I-', slot # x5]."""
    if not mask:
        raise ValueError("mask is empty")
    tokens: list[dict] = []
    for match in re.finditer(r"A+|#+|[^A#]+", mask):
        text = match.group(0)
        if text[0] in SLOT_CLASSES:
            tokens.append({"slot": text[0], "length": len(text)})
        else:
            tokens.append({"literal": text})
    if not any("slot" in token for token in tokens):
        raise ValueError(f"mask {mask!r} has no letter (A) or digit (#) positions")
    return tokens


def mask_pattern(mask: str) -> str:
    """The full-match regex for a completely filled-in value."""
    parts = []
    for token in mask_tokens(mask):
        if "slot" in token:
            parts.append(f"{SLOT_CLASSES[token['slot']]}{{{token['length']}}}")
        else:
            parts.append(_escape(token["literal"]))
    return "^" + "".join(parts) + "$"


def mask_code(mask: str, value: str) -> str | None:
    """The leading letter run of a complete value: 'XOM' from 'XOM-I-00001'."""
    first = mask_tokens(mask)[0]
    if first.get("slot") != "A" or not re.match(mask_pattern(mask), value or ""):
        return None
    return value[: first["length"]]
