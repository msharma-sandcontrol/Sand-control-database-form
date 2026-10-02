"""Selected units survive flattening, including blank and hidden fields."""
from __future__ import annotations

from decimal import Decimal

import pytest

from db.mapping import MappingError, build_record_out, flatten_bucket


def test_blank_unit_is_stored_and_reconstructed(make_payload):
    well = make_payload()["well"]
    well["Well Specific"]["Sand Production & Well Performance"]["Initial PI"] = {
        "value": None, "unit": "Sm³ liquid/d/kPa",
    }
    flat = flatten_bucket(well, "well")
    assert flat["initial_pi_unit"] == "Sm³ liquid/d/kPa"
    assert "initial_pi" not in flat
    rebuilt = build_record_out(flat, "well")
    assert rebuilt["Well Specific"]["Sand Production & Well Performance"]["Initial PI"] == {
        "value": None, "unit": "Sm³ liquid/d/kPa",
    }


def test_hidden_blank_keeps_unit_but_hidden_answer_is_rejected(make_payload):
    well = make_payload(sand_failure="No")["well"]
    group = well["Well Specific"]["Sand Production & Well Performance"]
    group["Sand production rate at first choke back"] = {"value": None, "unit": "mg/Sm³ gas"}
    flat = flatten_bucket(well, "well")
    assert flat["sand_production_rate_at_first_choke_back_unit"] == "mg/Sm³ gas"
    group["Sand production rate at first choke back"]["value"] = "10"
    with pytest.raises(MappingError, match="hidden"):
        flatten_bucket(well, "well")


def test_temperature_limits_follow_selected_celsius_unit(make_payload):
    sand = make_payload()["completion_intervals"][0]["sand_bodies"][0]
    group = sand.setdefault("Reservoir Characterization", {}).setdefault(
        "Reservoir Rock and Fluid Properties", {}
    )
    group["Reservoir Temperature"] = {"value": "-10", "unit": "°C"}
    flat = flatten_bucket(sand, "sand_body")
    assert flat["reservoir_temperature_unit"] == "°C"
    assert float(flat["reservoir_temperature"]) == -10
    group["Reservoir Temperature"]["value"] = "-20"
    with pytest.raises(MappingError, match="below the minimum"):
        flatten_bucket(sand, "sand_body")


def test_invalid_unit_is_rejected(make_payload):
    well = make_payload()["well"]
    well["Well Specific"]["Well & Field Identification"]["Well TD, MD"] = {
        "value": "100", "unit": "furlongs",
    }
    with pytest.raises(MappingError, match="not allowed"):
        flatten_bucket(well, "well")


def test_gas_basis_keeps_zero_minimum(make_payload):
    well = make_payload(sand_failure="Yes")["well"]
    group = well["Well Specific"]["Sand Production & Well Performance"]
    group["Sand rate quantification"] = "Measurable"
    group["Sand production rate at first choke back"] = {
        "value": "-1", "unit": "lb/MMSCF",
    }
    with pytest.raises(MappingError, match="below the minimum"):
        flatten_bucket(well, "well")


def test_conditional_oil_and_gas_fvf_use_distinct_saved_fields(make_payload):
    from dictionary.conditional_fields import GAS_FVF, OIL_FVF

    sand = make_payload()["completion_intervals"][0]["sand_bodies"][0]
    group = sand.setdefault("Reservoir Characterization", {}).setdefault(
        "Reservoir Rock and Fluid Properties", {}
    )
    group["Fluid Type"] = "Oil"
    group[OIL_FVF] = {"value": "1.234567", "unit": "rb/STB"}
    oil = flatten_bucket(sand, "sand_body")
    assert float(oil["oil_formation_volume_factor_bo_at_downhole_conditions"]) == 1.234567
    assert oil["oil_formation_volume_factor_bo_at_downhole_conditions_unit"] == "rb/STB"
    assert "gas_formation_volume_factor_bg_at_downhole_conditions" not in oil

    del group[OIL_FVF]
    group["Fluid Type"] = "Condensate"
    group[GAS_FVF] = {"value": "0.003456", "unit": "res ft³/scf"}
    gas = flatten_bucket(sand, "sand_body")
    assert float(gas["gas_formation_volume_factor_bg_at_downhole_conditions"]) == 0.003456
    assert gas["gas_formation_volume_factor_bg_at_downhole_conditions_unit"] == "res ft³/scf"
    assert "oil_formation_volume_factor_bo_at_downhole_conditions" not in gas
    rebuilt = build_record_out(gas, "sand_body")
    assert rebuilt["Reservoir Characterization"]["Reservoir Rock and Fluid Properties"][GAS_FVF] == {
        "value": "0.003456", "unit": "res ft³/scf",
    }
    group[OIL_FVF] = {"value": "1.23", "unit": "rb/STB"}
    with pytest.raises(MappingError, match="hidden"):
        flatten_bucket(sand, "sand_body")


def test_bg_reservoir_barrel_unit_is_valid(make_payload):
    from dictionary.conditional_fields import GAS_FVF

    sand = make_payload()["completion_intervals"][0]["sand_bodies"][0]
    group = sand.setdefault("Reservoir Characterization", {}).setdefault(
        "Reservoir Rock and Fluid Properties", {}
    )
    group["Fluid Type"] = "Dry Gas"
    group[GAS_FVF] = {"value": "0.001", "unit": "rb/scf"}
    flat = flatten_bucket(sand, "sand_body")
    assert flat["gas_formation_volume_factor_bg_at_downhole_conditions_unit"] == "rb/scf"


def test_numeric_api_readback_keeps_decimal_digits():
    rebuilt = build_record_out({
        "well_td_md": Decimal("123456789.123456789"),
        "well_td_md_unit": "ft",
    }, "well")
    assert rebuilt["Well Specific"]["Well & Field Identification"]["Well TD, MD"] == {
        "value": "123456789.123456789", "unit": "ft",
    }
