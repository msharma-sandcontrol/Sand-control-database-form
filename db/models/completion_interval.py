"""The `completion_interval` table -- one row per Completion Interval within
a lateral, plus the dictionary-driven columns generated from MASTER.xlsx's
Completion-Interval-scope parameters (see
db/generated/completion_interval_columns.py, never hand-edited).
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, UniqueConstraint, func
from sqlalchemy.orm import relationship

from db.base import Base
from db.generated.completion_interval_columns import COMPLETION_INTERVAL_COLUMNS

completion_interval_table = Table(
    "completion_interval",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("lateral_id", Integer, ForeignKey("well_lateral.id", ondelete="CASCADE"), nullable=False, index=True),
    # 1-based submission order within the lateral. NOT used for referential
    # integrity -- purely so GET can reconstruct the same "Completion
    # Interval 1, 2, ..." order the form submitted.
    Column("ordinal", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    *COMPLETION_INTERVAL_COLUMNS,
    UniqueConstraint("lateral_id", "ordinal", name="uq_completion_interval_lateral_ordinal"),
)


class CompletionInterval(Base):
    __table__ = completion_interval_table

    lateral = relationship("Lateral", back_populates="completion_intervals")
    sand_bodies = relationship(
        "SandBody",
        back_populates="completion_interval",
        cascade="all, delete-orphan",
        order_by="SandBody.ordinal",
    )
