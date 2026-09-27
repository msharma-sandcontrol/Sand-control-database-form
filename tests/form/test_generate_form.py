"""form/generate_form.py's unit rendering: the markup the page's script
relies on to preset, read and export units. (The committed HTML itself is
checked by CI's codegen drift check.)
"""
from __future__ import annotations

import importlib.util
import json
from html import unescape
from pathlib import Path

import pytest

from dictionary import classify_field, classify_units, load_dictionary
from dictionary.models import ParamRow

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_generator():
    # form/ is a script directory, not an installed package.
    spec = importlib.util.spec_from_file_location("generate_form", REPO_ROOT / "form" / "generate_form.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def _row(**overrides) -> ParamRow:
    base = dict(
        row_number=1, scope="Well", category="C", subcategory="S", parameter="P",
        input_type="Number", field_unit="", metric_unit="", affected_subcategory="", affected_parameter="",
        data_validation='{"Decimal"}', tooltip="", user_comment="",
    )
    base.update(overrides)
    return ParamRow(**base)


def test_unitless_row_renders_an_empty_unit_cell():
    assert gen.render_unit(_row(), "Field Unit") == '<span class="field-unit"></span>'


def test_same_unit_in_both_systems_renders_as_fixed_text():
    html = gen.render_unit(_row(field_unit="%", metric_unit="%"), "Metric Unit")
    assert html == '<span class="field-unit" data-unit="%">%</span>'


@pytest.mark.parametrize(("system", "selected"), [("Field Unit", "pptb or lb/mmscf"), ("Metric Unit", "mg/L")])
def test_selectable_unit_renders_a_two_option_dropdown_starting_on_the_systems_unit(system, selected):
    html = gen.render_unit(_row(field_unit="pptb or lb/mmscf", metric_unit="mg/L"), system)
    assert html.startswith('<select class="field-unit unit-select"')
    assert html.count("<option ") == 2
    assert '<option value="pptb or lb/mmscf"' in html and '<option value="mg/L"' in html
    assert f'<option value="{selected}" selected>' in html
    assert html.count(" selected>") == 1
    defaults = unescape(html.split('data-unit-defaults="')[1].split('"')[0])
    assert json.loads(defaults) == {"Field Unit": "pptb or lb/mmscf", "Metric Unit": "mg/L"}


def test_unit_system_row_has_no_blank_option():
    row = _row(parameter="Unit System", input_type="Dropdown Menu",
               data_validation='{"List": {"options": ["Field Unit", "Metric Unit"], "default": "Field Unit"}}')
    html = gen.render_control(row, classify_field(row), unit_system_preset="Metric Unit")
    assert 'data-role="unit-system"' in html
    assert 'value=""' not in html
    assert '<option value="Metric Unit" selected>' in html


def test_select_default_is_preselected_but_blank_stays_reachable():
    row = _row(input_type="Dropdown Menu", data_validation='{"List": {"options": ["A", "B"], "default": "B"}}')
    html = gen.render_control(row, classify_field(row))
    assert '<option value="">(Blank)</option>' in html
    assert '<option value="B" selected>' in html


def test_generated_form_wires_every_unit_bearing_row():
    rows = load_dictionary(REPO_ROOT / "MASTER.xlsx")
    html = gen.render_html(gen.build_model(rows))
    assert html.count('data-role="unit-system">') == 1  # the element, not the script's selector for it
    selectable = sum(1 for r in rows if classify_units(r).selectable)
    fixed = sum(1 for r in rows if len(classify_units(r).options) == 1)
    assert html.count('class="field-unit unit-select"') == selectable
    assert html.count('class="field-unit" data-unit=') == fixed
