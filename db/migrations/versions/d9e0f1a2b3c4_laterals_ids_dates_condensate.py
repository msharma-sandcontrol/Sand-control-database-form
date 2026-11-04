"""Add laterals between well and completion interval; IDs, dates, condensate.

Structure: a new `well_lateral` table (not "lateral", a reserved word in
Postgres) sits between `well` and
`completion_interval`. Every well has at least one lateral (its main bore);
a multilateral well has one per branch. TD (MD and TVD) and the
completion-interval counter move from the well to each lateral. Existing
rows are carried over: each well gets Lateral 1 holding its old TD and
counter values, and its completion intervals are re-parented to it.

Well columns, following the November SME round in MASTER.xlsx:
- "Well name (anonymized)" is removed; the masked Well ID replaces it.
- "Field name" is replaced by "Field identification number (anonymized)".
- "Is this a Multilateral Well?" and "Number of laterals" are added.
- The three "Time to ..." durations (days) become "Date of ..." dates. A
  duration cannot be turned into a date, so these are dropped and added.

Sand body: "Dew Point Pressure (Pd)" and "Condensate-to-Gas Ratio (CGR)"
are added, each with its unit column.

The SI pressure unit also changed from kPa to bar. Units are stored as text
next to each value, so that needs no schema change, and no company records
exist yet whose stored "kPa" labels would need converting.

Hand-authored (no live Postgres to autogenerate against); verified with
`alembic check` against a database upgraded to this revision.

Revision ID: d9e0f1a2b3c4
Revises: c8d1e2f3a4b5
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (well column, lateral column, type, well comment, lateral comment)
MOVED_TO_LATERAL = [
    ("well_td_md", "td_md", sa.Numeric(), "Well TD, MD", "TD, MD"),
    ("well_td_md_unit", "td_md_unit", sa.Text(), "Unit for Well TD, MD", "Unit for TD, MD"),
    ("well_td_tvd_rkb", "td_tvd_rkb", sa.Numeric(), "Well TD, TVD (RKB)", "TD, TVD (RKB)"),
    ("well_td_tvd_rkb_unit", "td_tvd_rkb_unit", sa.Text(), "Unit for Well TD, TVD (RKB)", "Unit for TD, TVD (RKB)"),
    ("number_of_completion_intervals", "number_of_completion_intervals", sa.Integer(),
     "Number of Completion Intervals", "Number of Completion Intervals"),
]
# (old duration column, comment, new date column, comment)
DURATIONS_TO_DATES = [
    ("time_to_first_choke_back", "Time to first choke back",
     "date_of_first_choke_back", "Date of first choke back"),
    ("time_to_well_shut_in_due_to_sand", "Time to well shut-in due to sand",
     "date_of_well_shut_in_due_to_sand", "Date of well shut-in due to sand"),
    ("time_to_complete_well_failure", "Time to complete well failure",
     "date_of_complete_well_failure", "Date of complete well failure"),
]
WELL_ADDED = [
    ("is_this_a_multilateral_well", sa.Boolean(), "Is this a Multilateral Well?"),
    ("number_of_laterals", sa.Integer(), "Number of laterals"),
    ("field_identification_number_anonymized", sa.Text(), "Field identification number (anonymized)"),
]
WELL_REMOVED = [
    ("well_name_anonymized", sa.Text(), "Well name (anonymized)"),
    ("field_name", sa.Text(), "Field name"),
]
SAND_BODY_ADDED = [
    ("dew_point_pressure_pd", sa.Numeric(), "Dew Point Pressure (Pd)"),
    ("dew_point_pressure_pd_unit", sa.Text(), "Unit for Dew Point Pressure (Pd)"),
    ("condensate_to_gas_ratio_cgr", sa.Numeric(), "Condensate-to-Gas Ratio (CGR)"),
    ("condensate_to_gas_ratio_cgr_unit", sa.Text(), "Unit for Condensate-to-Gas Ratio (CGR)"),
]


def upgrade() -> None:
    op.create_table(
        "well_lateral",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("well_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        *[sa.Column(new, type_, nullable=True, comment=comment) for _, new, type_, _, comment in MOVED_TO_LATERAL],
        sa.ForeignKeyConstraint(["well_id"], ["well.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("well_id", "ordinal", name="uq_well_lateral_well_ordinal"),
    )
    op.create_index("ix_well_lateral_well_id", "well_lateral", ["well_id"])

    old_cols = ", ".join(old for old, *_ in MOVED_TO_LATERAL)
    new_cols = ", ".join(new for _, new, *_ in MOVED_TO_LATERAL)
    op.execute(f"INSERT INTO well_lateral (well_id, ordinal, {new_cols}) SELECT id, 1, {old_cols} FROM well")

    op.add_column("completion_interval", sa.Column("lateral_id", sa.Integer(), nullable=True))
    op.execute("UPDATE completion_interval AS ci SET lateral_id = l.id "
               "FROM well_lateral AS l WHERE l.well_id = ci.well_id AND l.ordinal = 1")
    op.alter_column("completion_interval", "lateral_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("completion_interval_lateral_id_fkey", "completion_interval", "well_lateral",
                          ["lateral_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_completion_interval_lateral_id", "completion_interval", ["lateral_id"])
    op.drop_constraint("uq_completion_interval_well_ordinal", "completion_interval", type_="unique")
    op.drop_index("ix_completion_interval_well_id", table_name="completion_interval")
    op.drop_constraint("completion_interval_well_id_fkey", "completion_interval", type_="foreignkey")
    op.drop_column("completion_interval", "well_id")
    op.create_unique_constraint("uq_completion_interval_lateral_ordinal", "completion_interval",
                                ["lateral_id", "ordinal"])

    for old, *_ in MOVED_TO_LATERAL:
        op.drop_column("well", old)
    for name, _type, _comment in WELL_REMOVED:
        op.drop_column("well", name)
    for name, type_, comment in WELL_ADDED:
        op.add_column("well", sa.Column(name, type_, nullable=True, comment=comment))
    for old, _old_comment, new, new_comment in DURATIONS_TO_DATES:
        op.drop_column("well", old)
        op.add_column("well", sa.Column(new, sa.Date(), nullable=True, comment=new_comment))
    for name, type_, comment in SAND_BODY_ADDED:
        op.add_column("sand_body", sa.Column(name, type_, nullable=True, comment=comment))


def downgrade() -> None:
    for name, *_ in reversed(SAND_BODY_ADDED):
        op.drop_column("sand_body", name)
    for old, old_comment, new, _new_comment in reversed(DURATIONS_TO_DATES):
        op.drop_column("well", new)
        op.add_column("well", sa.Column(old, sa.Numeric(), nullable=True, comment=old_comment))
    for name, *_ in reversed(WELL_ADDED):
        op.drop_column("well", name)
    for name, type_, comment in WELL_REMOVED:
        op.add_column("well", sa.Column(name, type_, nullable=True, comment=comment))
    for old, _new, type_, comment, _ in MOVED_TO_LATERAL:
        op.add_column("well", sa.Column(old, type_, nullable=True, comment=comment))

    # Lateral 1 (the main bore) carries its TD and counter back to the well.
    # Intervals of any other lateral fold into the well after Lateral 1's, so
    # (well_id, ordinal) stays unique.
    sets = ", ".join(f"{old} = l.{new}" for old, new, *_ in MOVED_TO_LATERAL)
    op.execute(f"UPDATE well AS w SET {sets} FROM well_lateral AS l WHERE l.well_id = w.id AND l.ordinal = 1")
    op.add_column("completion_interval", sa.Column("well_id", sa.Integer(), nullable=True))
    # Dropped first: renumbering row by row could briefly collide with it.
    op.drop_constraint("uq_completion_interval_lateral_ordinal", "completion_interval", type_="unique")
    op.execute("""
        UPDATE completion_interval AS ci SET well_id = ranked.well_id, ordinal = ranked.new_ordinal
        FROM (
            SELECT ci2.id, l.well_id,
                   ROW_NUMBER() OVER (PARTITION BY l.well_id ORDER BY l.ordinal, ci2.ordinal) AS new_ordinal
            FROM completion_interval AS ci2 JOIN well_lateral AS l ON l.id = ci2.lateral_id
        ) AS ranked
        WHERE ranked.id = ci.id
    """)
    op.alter_column("completion_interval", "well_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("completion_interval_well_id_fkey", "completion_interval", "well",
                          ["well_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_completion_interval_well_id", "completion_interval", ["well_id"])
    op.create_unique_constraint("uq_completion_interval_well_ordinal", "completion_interval",
                                ["well_id", "ordinal"])
    op.drop_index("ix_completion_interval_lateral_id", table_name="completion_interval")
    op.drop_constraint("completion_interval_lateral_id_fkey", "completion_interval", type_="foreignkey")
    op.drop_column("completion_interval", "lateral_id")
    op.drop_index("ix_well_lateral_well_id", table_name="well_lateral")
    op.drop_table("well_lateral")
