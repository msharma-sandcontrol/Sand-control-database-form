"""Add "Date of first indication of sand control failure" to well.

An SME asked for the date sand control failure was first noticed, separate
from the first action taken (first choke back). It is an optional date shown
only when Sand Control Failure = Yes, so the column is nullable like every
dictionary-driven column.

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("well", sa.Column(
        "date_of_first_indication_of_sand_control_failure", sa.Date(), nullable=True,
        comment="Date of first indication of sand control failure",
    ))


def downgrade() -> None:
    op.drop_column("well", "date_of_first_indication_of_sand_control_failure")
