"""Apply the November SME wording edits and drop Well start-up date.

Three Parameters were renamed in MASTER.xlsx, which codegen re-slugifies
into new column names. They are written as in-place RENAME COLUMN so any
values survive (autogenerate would have shown each as a drop + add):

- Well "Sand failure" -> "Sand Control Failure"
- Sand Body "Virgin Reservoir Pressure" -> "... at the top of the sand body"
- Sand Body "Initial PI" -> "Initial PI of the sand body" (the Well-level
  "Initial PI" is a separate row and keeps its name)

"Well start-up date" was removed from the dictionary, so its column goes.
The other edits in this round (the "Well Specific" category renamed to
"Well Specific Information", "OHFP" added as an open-hole sand-control
option, and a fixed "in" unit on Drill Bit Size) change payload keys,
allow-lists, or display only. They are enforced at the API layer from
db/generated/field_registry.json and need no SQL change.

Hand-authored because no live Postgres was available to autogenerate
against, like the earlier rename migrations.

Revision ID: c8d1e2f3a4b5
Revises: b23c45d67e89
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "b23c45d67e89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, old column, new column, type, old comment, new comment)
RENAMES = [
    ("well", "sand_failure", "sand_control_failure", sa.Boolean(),
     "Sand failure", "Sand Control Failure"),
    ("sand_body", "virgin_reservoir_pressure", "virgin_reservoir_pressure_at_the_top_of_the_sand_body",
     sa.Numeric(), "Virgin Reservoir Pressure", "Virgin Reservoir Pressure at the top of the sand body"),
    ("sand_body", "virgin_reservoir_pressure_unit", "virgin_reservoir_pressure_at_the_top_of_the_sand_body_unit",
     sa.Text(), "Unit for Virgin Reservoir Pressure", "Unit for Virgin Reservoir Pressure at the top of the sand body"),
    ("sand_body", "initial_pi", "initial_pi_of_the_sand_body", sa.Numeric(),
     "Initial PI", "Initial PI of the sand body"),
    ("sand_body", "initial_pi_unit", "initial_pi_of_the_sand_body_unit", sa.Text(),
     "Unit for Initial PI", "Unit for Initial PI of the sand body"),
]


def upgrade() -> None:
    for table, old, new, type_, old_comment, new_comment in RENAMES:
        op.alter_column(table, old, new_column_name=new, existing_type=type_,
                        existing_nullable=True, existing_comment=old_comment, comment=new_comment)
    op.drop_column("well", "well_start_up_date")


def downgrade() -> None:
    op.add_column(
        "well",
        sa.Column("well_start_up_date", sa.Date(), nullable=True, comment="Well start-up date"),
    )
    for table, old, new, type_, old_comment, new_comment in reversed(RENAMES):
        op.alter_column(table, new, new_column_name=old, existing_type=type_,
                        existing_nullable=True, existing_comment=new_comment, comment=old_comment)
