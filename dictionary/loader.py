"""Reads the MasterView sheet of MASTER.xlsx into a list of ParamRow."""
from __future__ import annotations

from pathlib import Path

import openpyxl

from dictionary.models import ParamRow

SHEET_NAME = "MasterView"

# MasterView header -> ParamRow attribute. Columns are found by their header
# text rather than by position, so inserting or reordering a column in Excel
# fails loudly on a missing header instead of silently shifting every value
# after it into the wrong field.
COLUMNS = {
    "Row Number": "row_number",
    "Scope": "scope",
    "Category": "category",
    "Subcategory": "subcategory",
    "Parameter": "parameter",
    "Input Type": "input_type",
    "Field Unit": "field_unit",
    "Metric Unit": "metric_unit",
    "Affected Subcategory": "affected_subcategory",
    "Affected Parameter": "affected_parameter",
    "Data Validation": "data_validation",
    "Tooltip": "tooltip",
    "User comment": "user_comment",
}


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def load_dictionary(xlsx_path: Path) -> list[ParamRow]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    if SHEET_NAME not in wb.sheetnames:
        raise SystemExit(f"Sheet '{SHEET_NAME}' not found in {xlsx_path}. "
                          f"Available sheets: {', '.join(wb.sheetnames)}")
    ws = wb[SHEET_NAME]
    sheet_rows = ws.iter_rows(values_only=True)
    header = [_text(h) for h in next(sheet_rows, ())]
    missing = [name for name in COLUMNS if name not in header]
    if missing:
        raise SystemExit(f"Sheet '{SHEET_NAME}' in {xlsx_path} is missing column(s): {', '.join(missing)}. "
                          f"Found: {', '.join(h for h in header if h)}")
    positions = {attr: header.index(name) for name, attr in COLUMNS.items()}

    rows = []
    for r in sheet_rows:
        cells = {attr: (r[i] if i < len(r) else None) for attr, i in positions.items()}
        if not cells["parameter"]:
            continue
        rows.append(ParamRow(
            row_number=int(cells["row_number"]),
            **{attr: _text(value) for attr, value in cells.items() if attr != "row_number"},
        ))
    wb.close()
    return rows
