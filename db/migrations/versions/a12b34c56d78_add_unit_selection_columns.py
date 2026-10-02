"""Persist the chosen unit for each convertible measurement.

A unit remains meaningful when its number is blank: it is part of a saved
form state and determines how the next number will be interpreted. The form
and generated registry use the same choices; this migration adds their
explicit columns to each record level. No company records exist yet, so no
backfill or legacy conversion is required.

Revision ID: a12b34c56d78
Revises: d6e5a1b2c3f4
Create Date: 2026-09-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a12b34c56d78"
down_revision: Union[str, Sequence[str], None] = "d6e5a1b2c3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Kept here rather than imported from generated code: an applied migration
# must keep its original column set if MASTER.xlsx changes in the future.
UNIT_COLUMNS = {
    "well": [
        ("gas_rate_shut_in_unit", "Unit for Gas Rate @ Shut-in"),
        ("gas_rate_the_first_choke_back_unit", "Unit for Gas Rate @ The First Choke Back"),
        ("initial_pi_unit", "Unit for Initial PI"),
        ("max_drawdown_over_well_life_unit", "Unit for Max drawdown over well life"),
        ("oil_rate_shut_in_unit", "Unit for Oil Rate @ Shut-in"),
        ("oil_rate_the_first_choke_back_unit", "Unit for Oil Rate @ The First Choke Back"),
        ("p50_drawdown_over_well_life_unit", "Unit for P50 drawdown over well life"),
        ("peak_gas_rate_unit", "Unit for Peak gas rate"),
        ("peak_oil_rate_unit", "Unit for Peak oil rate"),
        ("peak_water_rate_unit", "Unit for Peak water rate"),
        ("sand_production_rate_at_complete_well_failure_unit", "Unit for Sand production rate at complete well failure"),
        ("sand_production_rate_at_first_choke_back_unit", "Unit for Sand production rate at first choke back"),
        ("sand_production_rate_at_well_shut_in_due_to_sand_unit", "Unit for Sand production rate at well shut-in due to sand"),
        ("water_depth_unit", "Unit for Water depth"),
        ("water_rate_shut_in_unit", "Unit for Water Rate @ Shut-in"),
        ("water_rate_the_first_choke_back_unit", "Unit for Water Rate @ The First Choke Back"),
        ("well_pi_after_choke_back_unit", "Unit for Well PI after choke-back"),
        ("well_td_md_unit", "Unit for Well TD, MD"),
        ("well_td_tvd_rkb_unit", "Unit for Well TD, TVD (RKB)"),
    ],
    "completion_interval": [
        ("bridging_agent_loading_unit", "Unit for Bridging Agent Loading"),
        ("carrier_fluid_density_unit", "Unit for Carrier Fluid Density"),
        ("casing_size_above_oh_unit", "Unit for Casing Size above OH"),
        ("casing_size_unit", "Unit for Casing Size"),
        ("gross_open_hole_length_unit", "Unit for Gross Open Hole Length"),
        ("gross_perf_length_unit", "Unit for Gross Perf Length"),
        ("hole_size_unit", "Unit for Hole Size"),
        ("max_proppant_concentration_unit", "Unit for Max Proppant Concentration"),
        ("max_pump_rate_unit", "Unit for Max Pump Rate"),
        ("net_pay_length_unit", "Unit for Net Pay Length"),
        ("net_perf_length_unit", "Unit for Net Perf Length"),
        ("net_pressure_gain_unit", "Unit for Net Pressure Gain"),
        ("ob_ob_magnitude_unit", "Unit for OB / OB Magnitude"),
        ("perf_packing_unit", "Unit for Perf Packing"),
        ("perforation_gun_size_unit", "Unit for Perforation Gun Size"),
        ("perforation_spf_unit", "Unit for Perforation SPF"),
        ("proppant_unit_length_unit", "Unit for Proppant / Unit Length"),
        ("reservoir_drilling_fluid_density_unit", "Unit for Reservoir Drilling Fluid Density"),
        ("screen_base_pipe_size_unit", "Unit for Screen Base Pipe Size"),
        ("screen_gauge_unit", "Unit for Screen Gauge"),
        ("weighting_agent_loading_unit", "Unit for Weighting Agent Loading"),
    ],
    "sand_body": [
        ("core_derived_min_rock_ucs_unit", "Unit for Core Derived Min Rock UCS"),
        ("core_derived_p50_rock_ucs_unit", "Unit for Core Derived P50 Rock UCS"),
        ("frac_gradient_unit", "Unit for Frac gradient"),
        ("initial_pi_unit", "Unit for Initial PI"),
        ("k_h_from_log_unit", "Unit for k.h from Log"),
        ("k_h_from_pta_unit", "Unit for k.h from PTA"),
        ("oil_bubble_point_pb_unit", "Unit for Oil Bubble Point (Pb)"),
        ("producing_fluid_viscosity_unit", "Unit for Producing Fluid Viscosity"),
        ("reservoir_pressure_at_first_sand_production_unit", "Unit for Reservoir pressure at first sand production"),
        ("reservoir_pressure_at_time_of_completion_unit", "Unit for Reservoir Pressure at Time of Completion"),
        ("reservoir_temperature_unit", "Unit for Reservoir Temperature"),
        ("rock_compressibility_at_first_sand_production_unit", "Unit for Rock compressibility at first sand production"),
        ("rock_compressibility_at_initial_reservoir_pressure_unit", "Unit for Rock compressibility at initial reservoir pressure"),
        ("solution_gas_ratio_rs_unit", "Unit for Solution Gas Ratio (Rs)"),
        ("virgin_reservoir_pressure_unit", "Unit for Virgin Reservoir Pressure"),
    ],
}


def upgrade() -> None:
    for table, columns in UNIT_COLUMNS.items():
        for name, comment in columns:
            op.add_column(table, sa.Column(name, sa.Text(), nullable=True, comment=comment))


def downgrade() -> None:
    for table, columns in UNIT_COLUMNS.items():
        for name, _ in reversed(columns):
            op.drop_column(table, name)
