"""The `well_lateral` table -- one row per lateral (wellbore branch) of a well,
plus the dictionary-driven columns generated from MASTER.xlsx's
Lateral-scope parameters (see db/generated/lateral_columns.py, never
hand-edited). A well that is not multilateral has exactly one lateral, its
main bore, so every completion interval hangs off a lateral either way.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, UniqueConstraint, func
from sqlalchemy.orm import relationship

from db.base import Base
from db.generated.lateral_columns import WELL_LATERAL_COLUMNS

# Not named "lateral": that is a reserved word in Postgres.
lateral_table = Table(
    "well_lateral",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("well_id", Integer, ForeignKey("well.id", ondelete="CASCADE"), nullable=False, index=True),
    # 1-based submission order within the well (Lateral 1 is the main bore).
    # NOT used for referential integrity -- only to rebuild the form's order.
    Column("ordinal", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    *WELL_LATERAL_COLUMNS,
    UniqueConstraint("well_id", "ordinal", name="uq_well_lateral_well_ordinal"),
)


class Lateral(Base):
    __table__ = lateral_table

    well = relationship("Well", back_populates="laterals")
    completion_intervals = relationship(
        "CompletionInterval",
        back_populates="lateral",
        cascade="all, delete-orphan",
        order_by="CompletionInterval.ordinal",
    )
