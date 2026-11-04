"""Laterals, counters, ID masks, condensate fields, and failure dates.

Most checks validate RecordIngest directly (no database). One submits a
multilateral record end to end to prove the lateral rows persist.
"""
from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from backend.app.schemas.ingest import RecordIngest
from db.mapping import LEVEL_LIMITS
from dictionary.masks import mask_code, mask_pattern

IDENT = ("Well Specific Information", "Well & Field Identification")
RESERVOIR = ("Reservoir Characterization", "Reservoir Rock and Fluid Properties")
MLT = "Is this a Multilateral Well?"


def _ident(payload: dict) -> dict:
    return payload["well"][IDENT[0]][IDENT[1]]


def _make_multilateral(payload: dict, n: int) -> dict:
    _ident(payload)[MLT] = "Yes"
    _ident(payload)["Number of laterals"] = n
    payload["laterals"] = [copy.deepcopy(payload["laterals"][0]) for _ in range(n)]
    return payload


def _counter(bucket: dict, category: str, subcategory: str, parameter: str, value) -> None:
    bucket.setdefault(category, {}).setdefault(subcategory, {})[parameter] = value


def test_limits_come_from_the_workbook_counters():
    assert LEVEL_LIMITS == {"lateral": 100, "completion_interval": 10, "sand_body": 10}


def test_single_well_has_exactly_one_lateral(make_payload):
    payload = make_payload()
    assert RecordIngest.model_validate(payload)
    payload["laterals"].append(copy.deepcopy(payload["laterals"][0]))
    with pytest.raises(ValidationError, match="not multilateral has exactly one lateral"):
        RecordIngest.model_validate(payload)


def test_multilateral_count_must_match_laterals(make_payload):
    payload = _make_multilateral(make_payload(), 3)
    assert RecordIngest.model_validate(payload)
    _ident(payload)["Number of laterals"] = 4
    with pytest.raises(ValidationError, match="Number of laterals is 4 but 3 laterals were sent"):
        RecordIngest.model_validate(payload)


def test_multilateral_needs_its_count(make_payload):
    payload = _make_multilateral(make_payload(), 2)
    del _ident(payload)["Number of laterals"]
    with pytest.raises(ValidationError, match="Number of laterals: this field is required"):
        RecordIngest.model_validate(payload)


def test_number_of_laterals_is_hidden_for_a_single_well(make_payload):
    payload = make_payload()
    _ident(payload)["Number of laterals"] = 2
    with pytest.raises(ValidationError, match="hidden by the current form answers"):
        RecordIngest.model_validate(payload)


def test_interval_and_sand_body_counters_must_match(make_payload):
    payload = make_payload()
    lateral = payload["laterals"][0]
    lateral["completion_intervals"].append(copy.deepcopy(lateral["completion_intervals"][0]))
    with pytest.raises(ValidationError, match="Lateral 1: Number of Completion Intervals is 1 but 2 were sent"):
        RecordIngest.model_validate(payload)
    _counter(lateral["fields"], "Lateral", "Lateral Details", "Number of Completion Intervals", 2)
    assert RecordIngest.model_validate(payload)
    interval = lateral["completion_intervals"][1]
    interval["sand_bodies"].append({})
    with pytest.raises(ValidationError, match="Completion Interval 2: Number of sand bodies is 1 but 2 were sent"):
        RecordIngest.model_validate(payload)


@pytest.mark.parametrize(("path", "level"), [
    (lambda p: p["laterals"][0]["completion_intervals"], "completion_interval"),
    (lambda p: p["laterals"][0]["completion_intervals"][0]["sand_bodies"], "sand_body"),
])
def test_block_lists_are_capped_and_never_empty(make_payload, path, level):
    payload = make_payload()
    blocks = path(payload)
    blocks[:] = [copy.deepcopy(blocks[0]) for _ in range(LEVEL_LIMITS[level] + 1)]
    with pytest.raises(ValidationError, match=f"at most {LEVEL_LIMITS[level]} items"):
        RecordIngest.model_validate(payload)
    blocks.clear()
    with pytest.raises(ValidationError, match="at least 1 item"):
        RecordIngest.model_validate(payload)


def test_mask_pattern_and_code():
    assert mask_pattern("AAA-I-#####") == "^[A-Z]{3}-I-[0-9]{5}$"
    assert mask_code("AAA-I-#####", "XOM-I-00001") == "XOM"
    assert mask_code("AAA-I-#####", "XOM-I-0001") is None


@pytest.mark.parametrize("bad", ["XOM-I-0001", "xom-I-00001", "XOM-F-00001", "XOMI00001", "XO1-I-00001"])
def test_well_id_must_follow_the_mask(make_payload, bad):
    payload = make_payload()
    _ident(payload)["Well identification number (anonymized)"] = bad
    with pytest.raises(ValidationError, match="does not match the required format"):
        RecordIngest.model_validate(payload)


def test_field_id_is_optional_but_must_share_the_company_code(make_payload):
    payload = make_payload()
    ident = _ident(payload)
    ident["Well identification number (anonymized)"] = "XOM-I-00001"
    assert RecordIngest.model_validate(payload)  # Field ID left blank
    ident["Field identification number (anonymized)"] = "XOM-F-001"
    assert RecordIngest.model_validate(payload)
    ident["Field identification number (anonymized)"] = "CVX-F-001"
    with pytest.raises(ValidationError, match="company code 'CVX' does not match"):
        RecordIngest.model_validate(payload)
    ident["Field identification number (anonymized)"] = "XOM-F-01"
    with pytest.raises(ValidationError, match="does not match the required format"):
        RecordIngest.model_validate(payload)


def _sand(payload: dict) -> dict:
    sand = payload["laterals"][0]["completion_intervals"][0]["sand_bodies"][0]
    return sand.setdefault(RESERVOIR[0], {}).setdefault(RESERVOIR[1], {})


def test_condensate_swaps_oil_properties_for_dew_point_and_cgr(make_payload):
    payload = make_payload(well_type="Gas Condensate Producer")
    group = _sand(payload)
    group["Fluid Type"] = "Condensate"
    group["Dew Point Pressure (Pd)"] = {"value": "250", "unit": "bar"}
    group["Condensate-to-Gas Ratio (CGR)"] = {"value": "60", "unit": "stb/MMscf"}
    assert RecordIngest.model_validate(payload)
    group["Oil Bubble Point (Pb)"] = {"value": "3000", "unit": "psi"}
    with pytest.raises(ValidationError, match="Oil Bubble Point .*hidden"):
        RecordIngest.model_validate(payload)


@pytest.mark.parametrize("fluid", ["Wet Gas", "Dry Gas"])
def test_wet_and_dry_gas_hide_oil_properties_and_condensate_fields(make_payload, fluid):
    payload = make_payload(well_type="Gas Producer")
    group = _sand(payload)
    group["Fluid Type"] = fluid
    for name, value in [("Solution Gas Ratio (Rs)", {"value": "500", "unit": "scf/stb"}),
                        ("Dew Point Pressure (Pd)", {"value": "250", "unit": "bar"})]:
        group[name] = value
        with pytest.raises(ValidationError, match="hidden"):
            RecordIngest.model_validate(payload)
        del group[name]


def test_failure_dates_take_iso_dates_not_durations(make_payload):
    payload = make_payload(sand_failure="Yes")
    performance = payload["well"]["Well Specific Information"]["Sand Production & Well Performance"]
    performance["Date of first choke back"] = "2024-05-06"
    assert RecordIngest.model_validate(payload)
    performance["Date of first choke back"] = "120"
    with pytest.raises(ValidationError, match="is not a YYYY-MM-DD date"):
        RecordIngest.model_validate(payload)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_multilateral_record_persists_and_reads_back(client, seeded_org, db_session, make_payload):
    _, token = seeded_org
    payload = _make_multilateral(make_payload(), 2)
    second = payload["laterals"][1]
    second["fields"]["Lateral"]["Lateral Details"]["TD, MD"] = {"value": "15000", "unit": "ft"}
    second["fields"]["Lateral"]["Lateral Details"]["Number of Completion Intervals"] = 2
    second["completion_intervals"].append(copy.deepcopy(second["completion_intervals"][0]))
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text

    from db.models import Well

    well = db_session.get(Well, resp.json()["id"])
    assert well.is_this_a_multilateral_well is True
    assert well.number_of_laterals == 2
    assert [lateral.ordinal for lateral in well.laterals] == [1, 2]
    assert float(well.laterals[1].td_md) == 15000
    assert [len(lateral.completion_intervals) for lateral in well.laterals] == [1, 2]

    body = client.get(f"/records/{well.id}", headers=_auth(token)).json()
    assert [len(lateral["completion_intervals"]) for lateral in body["laterals"]] == [1, 2]
