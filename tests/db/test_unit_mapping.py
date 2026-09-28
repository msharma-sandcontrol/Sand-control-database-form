"""Selected units survive flattening, including blank and hidden fields."""
from __future__ import annotations

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
