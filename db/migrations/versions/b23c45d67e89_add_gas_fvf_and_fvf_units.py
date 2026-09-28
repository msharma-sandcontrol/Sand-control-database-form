"""Distinguish Oil Bo and Gas Bg, with explicit units for each FVF value.

The workbook still numbers both conditional variants as row 145, so later
rows keep their existing numbers. Oil retains its existing numeric column;
Gas gets its own numeric column. Explicit unit columns preserve the selected
ratio notation even if a field has not yet been filled.

Revision ID: b23c45d67e89
Revises: a12b34c56d78
Create Date: 2026-09-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b23c45d67e89"
down_revision: Union[str, Sequence[str], None] = "a12b34c56d78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sand_body", sa.Column(
        "oil_formation_volume_factor_bo_at_downhole_conditions_unit", sa.Text(), nullable=True,
        comment="Unit for Oil Formation Volume Factor (Bo) at downhole conditions",
    ))
    op.add_column("sand_body", sa.Column(
        "gas_formation_volume_factor_bg_at_downhole_conditions", sa.Numeric(), nullable=True,
        comment="Gas Formation Volume Factor (Bg) at downhole conditions",
    ))
    op.add_column("sand_body", sa.Column(
        "gas_formation_volume_factor_bg_at_downhole_conditions_unit", sa.Text(), nullable=True,
        comment="Unit for Gas Formation Volume Factor (Bg) at downhole conditions",
    ))


def downgrade() -> None:
    op.drop_column("sand_body", "gas_formation_volume_factor_bg_at_downhole_conditions_unit")
    op.drop_column("sand_body", "gas_formation_volume_factor_bg_at_downhole_conditions")
    op.drop_column("sand_body", "oil_formation_volume_factor_bo_at_downhole_conditions_unit")
