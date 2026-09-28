"""Name the screen-size field for the selection method it records.

The other workbook change in this revision makes severity conditional on a
confirmed failure. It changes validation rules, not the well table shape.

Revision ID: d6e5a1b2c3f4
Revises: e41b59c2a7d3
Create Date: 2026-09-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e5a1b2c3f4"
down_revision: Union[str, Sequence[str], None] = "e41b59c2a7d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "completion_interval",
        "screen_size_selection",
        new_column_name="screen_size_selection_method",
        existing_type=sa.Text(),
        existing_nullable=True,
        existing_comment="Screen Size Selection",
        comment="Screen Size Selection Method",
    )


def downgrade() -> None:
    op.alter_column(
        "completion_interval",
        "screen_size_selection_method",
        new_column_name="screen_size_selection",
        existing_type=sa.Text(),
        existing_nullable=True,
        existing_comment="Screen Size Selection Method",
        comment="Screen Size Selection",
    )
