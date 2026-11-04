# GENERATED FILE -- DO NOT EDIT BY HAND.
# Regenerate with: python -m db.codegen   (source: MASTER.xlsx, sheet MasterView)
from sqlalchemy import Column, Integer, Numeric, Text

WELL_LATERAL_COLUMNS = [
    Column("td_md", Numeric, nullable=True, comment="TD, MD"),
    Column("td_md_unit", Text, nullable=True, comment="Unit for TD, MD"),
    Column("td_tvd_rkb", Numeric, nullable=True, comment="TD, TVD (RKB)"),
    Column("td_tvd_rkb_unit", Text, nullable=True, comment="Unit for TD, TVD (RKB)"),
    Column("number_of_completion_intervals", Integer, nullable=True, comment="Number of Completion Intervals"),
]
