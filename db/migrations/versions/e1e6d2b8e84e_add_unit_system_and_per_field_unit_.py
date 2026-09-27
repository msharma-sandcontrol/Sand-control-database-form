"""add unit system and per-field unit columns

MASTER.xlsx's single `Unit` column became two -- `Field Unit` (the old
column, renamed, values unchanged) and `Metric Unit` -- and a new Well-scope
"Unit System" dropdown (Field Unit / Metric Unit) presets which of the two
every field starts in; the form then lets each field's unit be changed on
its own. Values are stored exactly as entered, never converted, so a field
that offers a choice of units now records which one was used:

- `well.unit_system` -- the record's preset (a new dictionary Parameter).
- one `<column>_unit` Text column for each Parameter whose Field Unit and
  Metric Unit differ: 53 in all (19 well, 19 completion_interval, 15
  sand_body). A Parameter with the same unit in both systems (%, days, L,
  micron, md) needs no column -- the dictionary already says what it is.

Generated with `alembic revision --autogenerate` against a live Postgres at
a686239533ca -- the first migration in this chain that could be. The diff
was exactly these 54 columns and nothing else, which also confirms the
hand-authored migrations before it reproduce the models exactly. Added by
hand: the backfill below.

Backfill: until now every stored value was implicitly in its Parameter's
old `Unit` cell -- the same text as today's `Field Unit`, taken verbatim
(`pptb or lb/mmscf` is one label). So existing values get that unit recorded
explicitly, and every existing well gets unit_system = 'Field Unit'. Like
every migration's column list, the backfill is frozen literal data, never
read from the live dictionary.

Revision ID: e1e6d2b8e84e
Revises: a686239533ca
Create Date: 2026-09-27 01:59:06.175881

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1e6d2b8e84e'
down_revision: Union[str, Sequence[str], None] = 'a686239533ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, value column, the unit its existing values were entered in -- its
# Parameter's old `Unit` cell) for every new unit column.
_EXISTING_VALUE_UNITS = [
    ('completion_interval', 'casing_size_above_oh', 'inch'),
    ('completion_interval', 'hole_size', 'inch'),
    ('completion_interval', 'gross_open_hole_length', 'ft'),
    ('completion_interval', 'net_pay_length', 'ft'),
    ('completion_interval', 'reservoir_drilling_fluid_density', 'ppg'),
    ('completion_interval', 'casing_size', 'inch'),
    ('completion_interval', 'gross_perf_length', 'ft'),
    ('completion_interval', 'net_perf_length', 'ft'),
    ('completion_interval', 'perforation_gun_size', 'inch'),
    ('completion_interval', 'perforation_spf', 'shots/ft'),
    ('completion_interval', 'ob_ob_magnitude', 'psi'),
    ('completion_interval', 'screen_gauge', 'gauge or micron'),
    ('completion_interval', 'screen_base_pipe_size', 'inch'),
    ('completion_interval', 'proppant_unit_length', 'lbs/ft'),
    ('completion_interval', 'carrier_fluid_density', 'ppg'),
    ('completion_interval', 'perf_packing', 'lbs/ft'),
    ('completion_interval', 'max_proppant_concentration', 'ppa'),
    ('completion_interval', 'max_pump_rate', 'bpm'),
    ('completion_interval', 'net_pressure_gain', 'psi'),
    ('sand_body', 'virgin_reservoir_pressure', 'psi'),
    ('sand_body', 'reservoir_pressure_at_time_of_completion', 'psi'),
    ('sand_body', 'reservoir_pressure_at_first_sand_production', 'psi'),
    ('sand_body', 'reservoir_temperature', 'degF'),
    ('sand_body', 'core_derived_min_rock_ucs', 'psi'),
    ('sand_body', 'core_derived_p50_rock_ucs', 'psi'),
    ('sand_body', 'rock_compressibility_at_initial_reservoir_pressure', 'microsips'),
    ('sand_body', 'rock_compressibility_at_first_sand_production', 'microsips'),
    ('sand_body', 'initial_pi', 'stb/d/psi or mmscf/d/psi'),
    ('sand_body', 'k_h_from_pta', 'md-ft'),
    ('sand_body', 'k_h_from_log', 'md-ft'),
    ('sand_body', 'producing_fluid_viscosity', 'cP'),
    ('sand_body', 'oil_bubble_point_pb', 'psi'),
    ('sand_body', 'solution_gas_ratio_rs', 'scf/stb'),
    ('sand_body', 'frac_gradient', 'ppg'),
    ('well', 'water_depth', 'ft'),
    ('well', 'well_td_md', 'ft'),
    ('well', 'well_td_tvd_rkb', 'ft'),
    ('well', 'sand_production_rate_at_first_choke_back', 'pptb or lb/mmscf'),
    ('well', 'sand_production_rate_at_well_shut_in_due_to_sand', 'pptb or lb/mmscf'),
    ('well', 'sand_production_rate_at_complete_well_failure', 'pptb or lb/mmscf'),
    ('well', 'initial_pi', 'stb/d/psi or mmscf/d/psi'),
    ('well', 'well_pi_after_choke_back', 'stb/d/psi or mmscf/d/psi'),
    ('well', 'oil_rate_the_first_choke_back', 'stb/d'),
    ('well', 'oil_rate_shut_in', 'stb/d'),
    ('well', 'gas_rate_the_first_choke_back', 'mmscf/d'),
    ('well', 'gas_rate_shut_in', 'mmscf/d'),
    ('well', 'water_rate_the_first_choke_back', 'stb/d'),
    ('well', 'water_rate_shut_in', 'stb/d'),
    ('well', 'peak_oil_rate', 'stb/d'),
    ('well', 'peak_gas_rate', 'mmscf/d'),
    ('well', 'peak_water_rate', 'stb/d'),
    ('well', 'max_drawdown_over_well_life', 'psi'),
    ('well', 'p50_drawdown_over_well_life', 'psi'),
]


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('completion_interval', sa.Column('casing_size_above_oh_unit', sa.Text(), nullable=True, comment='Unit for Casing Size above OH'))
    op.add_column('completion_interval', sa.Column('hole_size_unit', sa.Text(), nullable=True, comment='Unit for Hole Size'))
    op.add_column('completion_interval', sa.Column('gross_open_hole_length_unit', sa.Text(), nullable=True, comment='Unit for Gross Open Hole Length'))
    op.add_column('completion_interval', sa.Column('net_pay_length_unit', sa.Text(), nullable=True, comment='Unit for Net Pay Length'))
    op.add_column('completion_interval', sa.Column('reservoir_drilling_fluid_density_unit', sa.Text(), nullable=True, comment='Unit for Reservoir Drilling Fluid Density'))
    op.add_column('completion_interval', sa.Column('casing_size_unit', sa.Text(), nullable=True, comment='Unit for Casing Size'))
    op.add_column('completion_interval', sa.Column('gross_perf_length_unit', sa.Text(), nullable=True, comment='Unit for Gross Perf Length'))
    op.add_column('completion_interval', sa.Column('net_perf_length_unit', sa.Text(), nullable=True, comment='Unit for Net Perf Length'))
    op.add_column('completion_interval', sa.Column('perforation_gun_size_unit', sa.Text(), nullable=True, comment='Unit for Perforation Gun Size'))
    op.add_column('completion_interval', sa.Column('perforation_spf_unit', sa.Text(), nullable=True, comment='Unit for Perforation SPF'))
    op.add_column('completion_interval', sa.Column('ob_ob_magnitude_unit', sa.Text(), nullable=True, comment='Unit for OB / OB Magnitude'))
    op.add_column('completion_interval', sa.Column('screen_gauge_unit', sa.Text(), nullable=True, comment='Unit for Screen Gauge'))
    op.add_column('completion_interval', sa.Column('screen_base_pipe_size_unit', sa.Text(), nullable=True, comment='Unit for Screen Base Pipe Size'))
    op.add_column('completion_interval', sa.Column('proppant_unit_length_unit', sa.Text(), nullable=True, comment='Unit for Proppant / Unit Length'))
    op.add_column('completion_interval', sa.Column('carrier_fluid_density_unit', sa.Text(), nullable=True, comment='Unit for Carrier Fluid Density'))
    op.add_column('completion_interval', sa.Column('perf_packing_unit', sa.Text(), nullable=True, comment='Unit for Perf Packing'))
    op.add_column('completion_interval', sa.Column('max_proppant_concentration_unit', sa.Text(), nullable=True, comment='Unit for Max Proppant Concentration'))
    op.add_column('completion_interval', sa.Column('max_pump_rate_unit', sa.Text(), nullable=True, comment='Unit for Max Pump Rate'))
    op.add_column('completion_interval', sa.Column('net_pressure_gain_unit', sa.Text(), nullable=True, comment='Unit for Net Pressure Gain'))
    op.add_column('sand_body', sa.Column('virgin_reservoir_pressure_unit', sa.Text(), nullable=True, comment='Unit for Virgin Reservoir Pressure'))
    op.add_column('sand_body', sa.Column('reservoir_pressure_at_time_of_completion_unit', sa.Text(), nullable=True, comment='Unit for Reservoir Pressure at Time of Completion'))
    op.add_column('sand_body', sa.Column('reservoir_pressure_at_first_sand_production_unit', sa.Text(), nullable=True, comment='Unit for Reservoir pressure at first sand production'))
    op.add_column('sand_body', sa.Column('reservoir_temperature_unit', sa.Text(), nullable=True, comment='Unit for Reservoir Temperature'))
    op.add_column('sand_body', sa.Column('core_derived_min_rock_ucs_unit', sa.Text(), nullable=True, comment='Unit for Core Derived Min Rock UCS'))
    op.add_column('sand_body', sa.Column('core_derived_p50_rock_ucs_unit', sa.Text(), nullable=True, comment='Unit for Core Derived P50 Rock UCS'))
    op.add_column('sand_body', sa.Column('rock_compressibility_at_initial_reservoir_pressure_unit', sa.Text(), nullable=True, comment='Unit for Rock compressibility at initial reservoir pressure'))
    op.add_column('sand_body', sa.Column('rock_compressibility_at_first_sand_production_unit', sa.Text(), nullable=True, comment='Unit for Rock compressibility at first sand production'))
    op.add_column('sand_body', sa.Column('initial_pi_unit', sa.Text(), nullable=True, comment='Unit for Initial PI'))
    op.add_column('sand_body', sa.Column('k_h_from_pta_unit', sa.Text(), nullable=True, comment='Unit for k.h from PTA'))
    op.add_column('sand_body', sa.Column('k_h_from_log_unit', sa.Text(), nullable=True, comment='Unit for k.h from Log'))
    op.add_column('sand_body', sa.Column('producing_fluid_viscosity_unit', sa.Text(), nullable=True, comment='Unit for Producing Fluid Viscosity'))
    op.add_column('sand_body', sa.Column('oil_bubble_point_pb_unit', sa.Text(), nullable=True, comment='Unit for Oil Bubble Point (Pb)'))
    op.add_column('sand_body', sa.Column('solution_gas_ratio_rs_unit', sa.Text(), nullable=True, comment='Unit for Solution Gas Ratio (Rs)'))
    op.add_column('sand_body', sa.Column('frac_gradient_unit', sa.Text(), nullable=True, comment='Unit for Frac gradient'))
    op.add_column('well', sa.Column('unit_system', sa.Text(), nullable=True, comment='Unit System'))
    op.add_column('well', sa.Column('water_depth_unit', sa.Text(), nullable=True, comment='Unit for Water depth'))
    op.add_column('well', sa.Column('well_td_md_unit', sa.Text(), nullable=True, comment='Unit for Well TD, MD'))
    op.add_column('well', sa.Column('well_td_tvd_rkb_unit', sa.Text(), nullable=True, comment='Unit for Well TD, TVD (RKB)'))
    op.add_column('well', sa.Column('sand_production_rate_at_first_choke_back_unit', sa.Text(), nullable=True, comment='Unit for Sand production rate at first choke back'))
    op.add_column('well', sa.Column('sand_production_rate_at_well_shut_in_due_to_sand_unit', sa.Text(), nullable=True, comment='Unit for Sand production rate at well shut-in due to sand'))
    op.add_column('well', sa.Column('sand_production_rate_at_complete_well_failure_unit', sa.Text(), nullable=True, comment='Unit for Sand production rate at complete well failure'))
    op.add_column('well', sa.Column('initial_pi_unit', sa.Text(), nullable=True, comment='Unit for Initial PI'))
    op.add_column('well', sa.Column('well_pi_after_choke_back_unit', sa.Text(), nullable=True, comment='Unit for Well PI after choke-back'))
    op.add_column('well', sa.Column('oil_rate_the_first_choke_back_unit', sa.Text(), nullable=True, comment='Unit for Oil Rate @ The First Choke Back'))
    op.add_column('well', sa.Column('oil_rate_shut_in_unit', sa.Text(), nullable=True, comment='Unit for Oil Rate @ Shut-in'))
    op.add_column('well', sa.Column('gas_rate_the_first_choke_back_unit', sa.Text(), nullable=True, comment='Unit for Gas Rate @ The First Choke Back'))
    op.add_column('well', sa.Column('gas_rate_shut_in_unit', sa.Text(), nullable=True, comment='Unit for Gas Rate @ Shut-in'))
    op.add_column('well', sa.Column('water_rate_the_first_choke_back_unit', sa.Text(), nullable=True, comment='Unit for Water Rate @ The First Choke Back'))
    op.add_column('well', sa.Column('water_rate_shut_in_unit', sa.Text(), nullable=True, comment='Unit for Water Rate @ Shut-in'))
    op.add_column('well', sa.Column('peak_oil_rate_unit', sa.Text(), nullable=True, comment='Unit for Peak oil rate'))
    op.add_column('well', sa.Column('peak_gas_rate_unit', sa.Text(), nullable=True, comment='Unit for Peak gas rate'))
    op.add_column('well', sa.Column('peak_water_rate_unit', sa.Text(), nullable=True, comment='Unit for Peak water rate'))
    op.add_column('well', sa.Column('max_drawdown_over_well_life_unit', sa.Text(), nullable=True, comment='Unit for Max drawdown over well life'))
    op.add_column('well', sa.Column('p50_drawdown_over_well_life_unit', sa.Text(), nullable=True, comment='Unit for P50 drawdown over well life'))
    # ### end Alembic commands ###

    _backfill_units()


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('well', 'p50_drawdown_over_well_life_unit')
    op.drop_column('well', 'max_drawdown_over_well_life_unit')
    op.drop_column('well', 'peak_water_rate_unit')
    op.drop_column('well', 'peak_gas_rate_unit')
    op.drop_column('well', 'peak_oil_rate_unit')
    op.drop_column('well', 'water_rate_shut_in_unit')
    op.drop_column('well', 'water_rate_the_first_choke_back_unit')
    op.drop_column('well', 'gas_rate_shut_in_unit')
    op.drop_column('well', 'gas_rate_the_first_choke_back_unit')
    op.drop_column('well', 'oil_rate_shut_in_unit')
    op.drop_column('well', 'oil_rate_the_first_choke_back_unit')
    op.drop_column('well', 'well_pi_after_choke_back_unit')
    op.drop_column('well', 'initial_pi_unit')
    op.drop_column('well', 'sand_production_rate_at_complete_well_failure_unit')
    op.drop_column('well', 'sand_production_rate_at_well_shut_in_due_to_sand_unit')
    op.drop_column('well', 'sand_production_rate_at_first_choke_back_unit')
    op.drop_column('well', 'well_td_tvd_rkb_unit')
    op.drop_column('well', 'well_td_md_unit')
    op.drop_column('well', 'water_depth_unit')
    op.drop_column('well', 'unit_system')
    op.drop_column('sand_body', 'frac_gradient_unit')
    op.drop_column('sand_body', 'solution_gas_ratio_rs_unit')
    op.drop_column('sand_body', 'oil_bubble_point_pb_unit')
    op.drop_column('sand_body', 'producing_fluid_viscosity_unit')
    op.drop_column('sand_body', 'k_h_from_log_unit')
    op.drop_column('sand_body', 'k_h_from_pta_unit')
    op.drop_column('sand_body', 'initial_pi_unit')
    op.drop_column('sand_body', 'rock_compressibility_at_first_sand_production_unit')
    op.drop_column('sand_body', 'rock_compressibility_at_initial_reservoir_pressure_unit')
    op.drop_column('sand_body', 'core_derived_p50_rock_ucs_unit')
    op.drop_column('sand_body', 'core_derived_min_rock_ucs_unit')
    op.drop_column('sand_body', 'reservoir_temperature_unit')
    op.drop_column('sand_body', 'reservoir_pressure_at_first_sand_production_unit')
    op.drop_column('sand_body', 'reservoir_pressure_at_time_of_completion_unit')
    op.drop_column('sand_body', 'virgin_reservoir_pressure_unit')
    op.drop_column('completion_interval', 'net_pressure_gain_unit')
    op.drop_column('completion_interval', 'max_pump_rate_unit')
    op.drop_column('completion_interval', 'max_proppant_concentration_unit')
    op.drop_column('completion_interval', 'perf_packing_unit')
    op.drop_column('completion_interval', 'carrier_fluid_density_unit')
    op.drop_column('completion_interval', 'proppant_unit_length_unit')
    op.drop_column('completion_interval', 'screen_base_pipe_size_unit')
    op.drop_column('completion_interval', 'screen_gauge_unit')
    op.drop_column('completion_interval', 'ob_ob_magnitude_unit')
    op.drop_column('completion_interval', 'perforation_spf_unit')
    op.drop_column('completion_interval', 'perforation_gun_size_unit')
    op.drop_column('completion_interval', 'net_perf_length_unit')
    op.drop_column('completion_interval', 'gross_perf_length_unit')
    op.drop_column('completion_interval', 'casing_size_unit')
    op.drop_column('completion_interval', 'reservoir_drilling_fluid_density_unit')
    op.drop_column('completion_interval', 'net_pay_length_unit')
    op.drop_column('completion_interval', 'gross_open_hole_length_unit')
    op.drop_column('completion_interval', 'hole_size_unit')
    op.drop_column('completion_interval', 'casing_size_above_oh_unit')
    # ### end Alembic commands ###


def _backfill_units() -> None:
    well = sa.table("well", sa.column("unit_system"))
    op.execute(well.update().values(unit_system="Field Unit"))
    for table_name, value_column, unit in _EXISTING_VALUE_UNITS:
        unit_column = f"{value_column}_unit"
        table = sa.table(table_name, sa.column(value_column), sa.column(unit_column))
        op.execute(table.update().where(table.c[value_column].isnot(None)).values({unit_column: unit}))
