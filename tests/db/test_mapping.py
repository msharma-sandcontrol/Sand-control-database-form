"""db.mapping's unit handling, against the real field registry: values and
their units in, {db_column: value} out, and back. No database needed --
these are the same functions the API's validation and persistence call.

Uses the sand_body / completion_interval scopes, which have no required
fields, so each test's bucket can hold just the field under test.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from db.mapping import DEFAULT_UNIT_SYSTEM, MappingError, build_record_out, flatten_bucket, resolve_unit_system

ROCK = ("Reservoir Characterization", "Reservoir Rock and Fluid Properties")


def _rock(parameter: str, value) -> dict:
    return {ROCK[0]: {ROCK[1]: {parameter: value}}}


def test_explicit_unit_is_stored_alongside_the_value():
    flat = flatten_bucket(_rock("Virgin Reservoir Pressure", {"value": "20684", "unit": "kPa"}), scope="sand_body")
    assert flat == {"virgin_reservoir_pressure": Decimal("20684"), "virgin_reservoir_pressure_unit": "kPa"}


def test_bare_value_takes_the_unit_systems_starting_unit():
    bucket = _rock("Virgin Reservoir Pressure", 3000)
    field = flatten_bucket(bucket, scope="sand_body")
    metric = flatten_bucket(bucket, scope="sand_body", unit_system="Metric Unit")
    assert field == {"virgin_reservoir_pressure": Decimal(3000), "virgin_reservoir_pressure_unit": "psi"}
    assert metric == {"virgin_reservoir_pressure": Decimal(3000), "virgin_reservoir_pressure_unit": "kPa"}


def test_either_systems_unit_is_accepted_whatever_the_unit_system():
    bucket = {"Completion": {"Liners and Screens": {"Screen Gauge": {"value": 305, "unit": "micron"}}}}
    flat = flatten_bucket(bucket, scope="completion_interval")
    assert flat == {"screen_gauge": Decimal("305"), "screen_gauge_unit": "micron"}


def test_an_or_label_is_stored_verbatim():
    flat = flatten_bucket(_rock("Initial PI", 2.5), scope="sand_body")
    assert flat == {"initial_pi": Decimal("2.5"), "initial_pi_unit": "stb/d/psi or mmscf/d/psi"}


def test_part_of_an_or_label_is_not_a_unit():
    # "stb/d/psi or mmscf/d/psi" is one label; its halves aren't options.
    with pytest.raises(MappingError, match="'stb/d/psi' is not one of"):
        flatten_bucket(_rock("Initial PI", {"value": 2.5, "unit": "stb/d/psi"}), scope="sand_body")


def test_unit_not_offered_by_the_dictionary_is_rejected():
    with pytest.raises(MappingError, match="'bar' is not one of"):
        flatten_bucket(_rock("Virgin Reservoir Pressure", {"value": 1, "unit": "bar"}), scope="sand_body")


def test_fixed_unit_needs_no_column_but_is_still_checked():
    assert flatten_bucket(_rock("Porosity", {"value": 25, "unit": "%"}), scope="sand_body") == {
        "porosity": Decimal("25"),
    }
    with pytest.raises(MappingError, match="'fraction' is not one of"):
        flatten_bucket(_rock("Porosity", {"value": 0.25, "unit": "fraction"}), scope="sand_body")


def test_unitless_field_accepts_the_object_form_but_no_unit():
    assert flatten_bucket(_rock("Fluid Type", {"value": "Oil"}), scope="sand_body") == {"fluid_type": "Oil"}
    with pytest.raises(MappingError, match="has no unit"):
        flatten_bucket(_rock("Fluid Type", {"value": "Oil", "unit": "psi"}), scope="sand_body")


def test_blank_value_stores_nothing_not_even_its_unit():
    assert flatten_bucket(_rock("Virgin Reservoir Pressure", {"value": "", "unit": "kPa"}), scope="sand_body") == {}


@pytest.mark.parametrize("value", [{"unit": "kPa"}, {"value": 1, "units": "kPa"}])
def test_malformed_value_object_is_rejected(value):
    with pytest.raises(MappingError, match="expected a value or"):
        flatten_bucket(_rock("Virgin Reservoir Pressure", value), scope="sand_body")


def test_multi_number_value_carries_one_shared_unit():
    flat = flatten_bucket(
        _rock("PSD D10/D25/D40/D50/D75/D90", {"value": [10, 25, 40, 50, 75, 90], "unit": "micron"}),
        scope="sand_body",
    )
    assert flat == {
        "psd_d10": Decimal(10), "psd_d25": Decimal(25), "psd_d40": Decimal(40),
        "psd_d50": Decimal(50), "psd_d75": Decimal(75), "psd_d90": Decimal(90),
    }


def test_build_record_out_returns_value_and_stored_unit():
    out = build_record_out(
        {"virgin_reservoir_pressure": Decimal("20684"), "virgin_reservoir_pressure_unit": "kPa"}, scope="sand_body",
    )
    assert out == _rock("Virgin Reservoir Pressure", {"value": 20684.0, "unit": "kPa"})


def test_build_record_out_fills_in_a_fixed_unit():
    assert build_record_out({"porosity": Decimal("25")}, scope="sand_body") == _rock(
        "Porosity", {"value": 25.0, "unit": "%"},
    )


def test_build_record_out_leaves_unitless_values_bare():
    assert build_record_out({"fluid_type": "Oil"}, scope="sand_body") == _rock("Fluid Type", "Oil")


def test_build_record_out_reports_an_unrecorded_unit_as_null():
    # Only possible for a value written outside both the API and the unit
    # migration's backfill -- reported as unknown rather than guessed.
    out = build_record_out({"initial_pi": Decimal("2")}, scope="sand_body")
    assert out == _rock("Initial PI", {"value": 2.0, "unit": None})


def test_flatten_then_build_round_trips():
    bucket = _rock("Reservoir Temperature", {"value": 90, "unit": "degC"})
    assert build_record_out(flatten_bucket(bucket, scope="sand_body"), scope="sand_body") == _rock(
        "Reservoir Temperature", {"value": 90.0, "unit": "degC"},
    )


def _well_with_unit_system(value) -> dict:
    return {"General Information": {"Data Origin & Disclosure": {"Unit System": value}}}


def test_resolve_unit_system():
    assert resolve_unit_system(None) == "Field Unit"
    assert resolve_unit_system({}) == "Field Unit"
    assert resolve_unit_system(_well_with_unit_system("Metric Unit")) == "Metric Unit"
    assert resolve_unit_system(_well_with_unit_system({"value": "Metric Unit"})) == "Metric Unit"
    # An invalid value is reported by the well bucket's own validation; for
    # reading bare values it just falls back to the default.
    assert resolve_unit_system(_well_with_unit_system("Imperial")) == "Field Unit"


def test_default_unit_system_is_the_dictionary_default():
    assert DEFAULT_UNIT_SYSTEM == "Field Unit"
