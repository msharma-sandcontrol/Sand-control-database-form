#!/usr/bin/env python3
"""Generate a standalone HTML intake form from the Sand Control Failure Data Dictionary.

Usage:
    python form/generate_form.py [input.xlsx] [output.html]

Input is the "MasterView" sheet of MASTER.xlsx, 12 columns in this order:
    Row Number, Scope, Category, Subcategory, Parameter, Input Type, Unit,
    Affected Subcategory, Affected Parameter, Data Validation, Tooltip, User comment

The dictionary-parsing layer (ParamRow, FieldSpec, load_dictionary,
classify_field, and the cell-DSL parsers) lives in the top-level `dictionary`
package and is shared with `db/codegen.py`, so the form and the database
schema are always derived from the exact same interpretation of MASTER.xlsx.
See CLAUDE.md for the full data model. Key points this generator relies on:

- `Row Number` is each row's 1-based position in MasterView. It is rendered
  next to every field, zero-padded to 3 digits (e.g. "001", "025", "114"),
  so a submitted/rendered field can be cross-referenced back to its exact
  spreadsheet row.
- `Scope` is one of "Well", "Lateral {id}", "Completion Interval {id}",
  "Sand Body {id}" -- a well has one or more Laterals (just its main bore
  unless it is multilateral), each with one or more Completion Intervals,
  each with one or more Sand Bodies. The form renders three nested,
  repeatable block levels, each sized by its counter field (see
  dictionary/structure.py).
- `Data Validation`, `Affected Subcategory` and `Affected Parameter` cells are
  written as Python-literal-safe text (parsed with ast.literal_eval, tolerant
  of JSON's lowercase true/false/null). Data Validation cells are a type name
  plus optional modifiers, e.g. `{"Decimal": {"min": 0}}`, `{"List":
  {"options": ["A", "B"], "required": True}}`, `{"Text Length": {"min": 7,
  "pattern": "alphanumeric"}}`, or a bare `{"Short Date"}` when there's
  nothing to constrain. In the Affected columns, a target listed as a plain
  set member means "start hidden, SHOW when this trigger value is selected"
  (the original convention); a target mapped to `False` means "start
  visible, HIDE when this trigger value is selected" (the newer exclude
  convention). Both can apply to the same target.

Requires: openpyxl (pip install openpyxl)
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

# Allow `python form/generate_form.py` to find the top-level `dictionary`
# package regardless of the current working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dictionary import (  # noqa: E402
    COMPLETION_SCOPE,
    CURRENT_SCHEMA_VERSION,
    LATERAL_SCOPE,
    SAND_BODY_SCOPE,
    WELL_SCOPE,
    FieldSpec,
    ParamRow,
    build_visibility_rules,
    classify_field,
    group_by_category_subcategory,
    load_dictionary,
)
from dictionary.conditional_fields import GAS_FVF, OIL_FVF, expand_conditional_rows  # noqa: E402
from dictionary.masks import mask_tokens  # noqa: E402
from dictionary.structure import LEVELS, MULTILATERAL_PARAMETER, level_limits  # noqa: E402
from dictionary.units import BASIS_DRIVERS, basis_driver, choices_for  # noqa: E402
from form.tabbed_layout import TABBED_CSS, TABBED_JS  # noqa: E402

DEFAULT_INPUT = REPO_ROOT / "MASTER.xlsx"
# The official form uses the tabbed layout (form/tabbed_layout.py). The
# classic long-page layout is generated alongside it from the same workbook
# and form script, kept for reference but not linked anywhere.
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "sand_control_form.html"
DEFAULT_CLASSIC_OUTPUT = Path(__file__).resolve().parent / "sand_control_form_classic.html"
# Optional expiration for a form emailed out as a standalone file. When set
# (here or with --expires-on YYYY-MM-DD), the date is baked in at generation
# time and checked by the browser on every load, which then locks the form.
# Not tamper-proof, but enough to retire an old copy without a backend.
# Empty means the form never expires (the current default).
DEFAULT_EXPIRES_ON = ""

WELL_ZONE_CLASS = {
    "General Information": "zone-general",
    "Well Specific Information": "zone-well",
}

# Each level's counter is the only way to change that level's size: leaving
# the box (or Enter, or its arrows) adds or removes blocks to match. A counter
# whose minimum is 1 starts at 1, matching the one block every level has.
COUNTER_ROLES = {level.counter: level.key for level in LEVELS}

# The masked Well-scope ID (e.g. XOM-I-00001) names exported files, so a
# reviewer can tell records apart without opening them. Until it is complete
# the file is named "Unnamed". Matched by exact Parameter name.
EXPORT_NAME_PARAM = "Well identification number (anonymized)"


# --------------------------------------------------------------------------
# Conditional-visibility model (rendering-only concern -- the DB layer stores
# every field regardless of the form's show/hide rules, so this stays local
# rather than moving into the shared dictionary package).
# --------------------------------------------------------------------------

def build_model(rows: list[ParamRow]) -> dict:
    rows = expand_conditional_rows(rows)
    well_rows = [r for r in rows if r.scope == WELL_SCOPE]
    lateral_rows = [r for r in rows if r.scope == LATERAL_SCOPE]
    completion_rows = [r for r in rows if r.scope == COMPLETION_SCOPE]
    sand_body_rows = [r for r in rows if r.scope == SAND_BODY_SCOPE]

    return {
        "limits": level_limits(rows),
        "well": group_by_category_subcategory(well_rows),
        "lateral": group_by_category_subcategory(lateral_rows),
        "completion": group_by_category_subcategory(completion_rows),
        "sand_body": group_by_category_subcategory(sand_body_rows),
        **build_visibility_rules(rows),
    }


# The option VALUE stays exactly as defined by MASTER.xlsx and the API. Only
# the visible wording adds practical metric equivalents for fixed thresholds.
CHOICE_DISPLAY = {'Shelf Offshore (< 3,000 ft)': 'Shelf Offshore (< 3,000 ft / 914.4 m)', 'Deepwater Offshore (3,000 - 6,000 ft)': 'Deepwater Offshore (3,000–6,000 ft / 914.4–1,828.8 m)', 'Ultra-Deepwater Offshore (> 6,000 ft)': 'Ultra-Deepwater Offshore (> 6,000 ft / 1,828.8 m)', 'Minor (<0.2 lb/1000 bbl)': 'Minor (<0.2 lb/1000 bbl / 0.571 mg/L liquid)', 'Moderate (0.2 to 2 lb/1000 bbl)': 'Moderate (0.2–2 lb/1000 bbl / 0.571–5.706 mg/L liquid)', 'Severe (2 to 10 lb/1000 bbl)': 'Severe (2–10 lb/1000 bbl / 5.706–28.530 mg/L liquid)', 'Catastrophic (>10 lb/1000 bbl)': 'Catastrophic (>10 lb/1000 bbl / 28.530 mg/L liquid)', 'Minor (<0.01 lb/MMSCF)': 'Minor (<0.01 lb/MMSCF / 0.160 mg/Sm³ gas)', 'Moderate (0.01 to 0.05 lb/MMSCF)': 'Moderate (0.01–0.05 lb/MMSCF / 0.160–0.801 mg/Sm³ gas)', 'Severe (0.05 to 0.2 lb/MMSCF)': 'Severe (0.05–0.2 lb/MMSCF / 0.801–3.204 mg/Sm³ gas)', 'Catastrophic (>0.2 lb/MMscf)': 'Catastrophic (>0.2 lb/MMSCF / 3.204 mg/Sm³ gas)', 'Gradual (≤ 0.01 in/hr average increase in choke diameter)': 'Gradual (≤ 0.01 in/hr / 0.0254 cm/hr average choke increase)', 'Aggressive (> 0.01 in/hr, or a single increase ≥ 0.05 in within 1 hr)': 'Aggressive (> 0.01 in/hr / 0.0254 cm/hr, or ≥ 0.05 in / 0.127 cm within 1 hr)'}


# --------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------

def esc(value) -> str:
    return html.escape(str(value), quote=True)


def build_show_hide_attr(category: str, name: str, show_rules: dict, hide_rules: dict) -> str:
    show = show_rules.get((category, name))
    hide = hide_rules.get((category, name))
    attrs = ""
    if show:
        expr = "||".join(f"{p}={v}" for p, v in show)
        attrs += f' data-show-if="{esc(expr)}"'
    if hide:
        expr = "||".join(f"{p}={v}" for p, v in hide)
        attrs += f' data-hide-if="{esc(expr)}"'
    if show:
        attrs += ' style="display:none"'
    return attrs


def render_control(row: ParamRow, spec: FieldSpec) -> str:
    dp = esc(row.parameter)
    req_attr = " required" if spec.required else ""
    if spec.kind == "select":
        # The placeholder is deliberately NOT `disabled`. A disabled option can be
        # the initial selection but can never be chosen again, so a user who picks
        # a value by mistake has no way back to "no answer" -- and that also strands
        # the optional selects that drive show/hide rules (Completion Type, the two
        # Sand Control Selected Method fields, Placement Method, Pack Efficiency
        # Source) in whichever branch was chosen first, with no neutral state to
        # return to. `required` is what enforces required-ness, so a blanked
        # required select is still invalid and still blocks export; making the
        # placeholder reachable weakens nothing.
        #
        # Optional fields label it "(Blank)" rather than "Select...", so the
        # placeholder also says that leaving the field blank is a real answer here.
        blank_label = "Select..." if spec.required else "(Blank)"
        options = [f'<option value="" selected>{blank_label}</option>']
        if spec.options_by:
            # The workbook holds the choices for each Well type. JavaScript
            # supplies the relevant list after the controlling answer changes.
            conditional = f' data-options-by="{esc(json.dumps(spec.options_by))}"'
        else:
            conditional = ""
            options += [f'<option value="{esc(o)}">{esc(CHOICE_DISPLAY.get(o, o))}</option>' for o in spec.options]
        return f'<select data-param="{dp}" data-kind="select"{conditional}{req_attr}>{"".join(options)}</select>'
    if spec.kind == "number":
        attrs = ""
        if row.parameter in COUNTER_ROLES:
            attrs += f' data-counter="{COUNTER_ROLES[row.parameter]}"'
            if spec.min_value == 1:
                attrs += ' value="1"'
        if spec.min_value is not None:
            attrs += f' min="{spec.min_value}"'
        if spec.max_value is not None:
            attrs += f' max="{spec.max_value}"'
        attrs += f' step="{spec.step or "any"}"'
        return (f'<input type="number"{attrs}{req_attr} data-param="{dp}" '
                f'data-kind="number" placeholder="Enter value">')
    if spec.kind == "date":
        return f'<input type="date"{req_attr} data-param="{dp}" data-kind="date">'
    if spec.kind == "multi_number":
        items = []
        for i, lbl in enumerate(spec.multi_labels):
            min_v = spec.multi_min_values[i] if i < len(spec.multi_min_values) else None
            max_v = spec.multi_max_values[i] if i < len(spec.multi_max_values) else None
            item_attrs = ""
            if min_v is not None:
                item_attrs += f' min="{min_v}"'
            if max_v is not None:
                item_attrs += f' max="{max_v}"'
            items.append(f'<span class="mn-item"><span class="mn-label">{esc(lbl)}</span>'
                         f'<input type="number" step="any"{item_attrs} class="mn-input"></span>')
        return f'<div class="multi-number" data-param="{dp}" data-kind="multi_number">{"".join(items)}</div>'
    if spec.mask:
        return render_masked(row, spec)
    if spec.kind == "text" and (spec.min_length is not None or spec.max_length is not None or spec.pattern):
        attrs = ""
        if spec.min_length is not None:
            attrs += f' minlength="{spec.min_length}"'
        if spec.max_length is not None:
            attrs += f' maxlength="{spec.max_length}"'
        if spec.pattern:
            attrs += f' pattern="{esc(spec.pattern)}"'
        return (f'<input type="text"{attrs}{req_attr} data-param="{dp}" '
                f'data-kind="text" placeholder="Enter text">')
    return f'<textarea rows="2"{req_attr} data-param="{dp}" data-kind="text" placeholder="Enter text"></textarea>'


def render_masked(row: ParamRow, spec: FieldSpec) -> str:
    """One box per letter/digit run of the mask with the fixed text between,
    e.g. [XOM]-I-[00001]. The JS joins the boxes into the saved value."""
    req_attr = " required" if spec.required else ""
    parts = []
    for token in mask_tokens(spec.mask):
        if "literal" in token:
            parts.append(f'<span class="mask-lit">{esc(token["literal"])}</span>')
            continue
        n = token["length"]
        if token["slot"] == "A":
            attrs = f'pattern="[A-Z]{{{n}}}" placeholder="{"ABC"[:n] if n <= 3 else "A" * n}" autocapitalize="characters"'
            label = "letters"
        else:
            attrs = f'pattern="[0-9]{{{n}}}" placeholder="{"0" * n}" inputmode="numeric"'
            label = "digits"
        parts.append(f'<input type="text" class="mask-seg" data-slot="{token["slot"]}" maxlength="{n}" '
                     f'style="--n:{n}" {attrs} autocomplete="off" spellcheck="false"{req_attr} '
                     f'aria-label="{esc(row.parameter)}, {n} {label}">')
    same = f' data-same-code-as="{esc(spec.same_code_as)}"' if spec.same_code_as else ""
    return (f'<span class="masked" data-param="{esc(row.parameter)}" data-kind="masked" '
            f'data-mask="{esc(spec.mask)}"{same}>{"".join(parts)}</span>')


def render_unit(row: ParamRow) -> str:
    choices = choices_for(row)
    if not choices:
        return '<span class="field-unit"></span>'
    if len(choices) == 1:
        unit = esc(choices[0]["unit"])
        return f'<span class="field-unit" data-unit="{unit}">{unit}</span>'
    options = "".join(
        f'<option value="{esc(choice["unit"])}">{esc(choice["unit"])}</option>'
        for choice in choices
    )
    data = esc(json.dumps(choices, ensure_ascii=False))
    driver = basis_driver(row)
    basis = f' data-unit-basis="{esc(driver)}"' if driver else ""
    return (f'<select class="field-unit unit-select" aria-label="Unit for {esc(row.parameter)}"{basis} '
            f'data-unit-choices="{data}" data-current-unit="{esc(choices[0]["unit"])}" '
            f'data-last-field-unit="{esc(choices[0]["unit"])}">{options}</select>')


def render_field_row(row: ParamRow, param_show: dict, param_hide: dict) -> str:
    spec = classify_field(row)
    control = render_control(row, spec)
    unit_html = render_unit(row)
    attrs = build_show_hide_attr(row.category, row.parameter, param_show, param_hide)
    req_mark = '<span class="required-mark">*</span>' if spec.required else ""
    tip_html = f'<span class="tt" tabindex="0" data-tip="{esc(row.tooltip)}">?</span>' if row.tooltip else ""
    # A counter's action cell explains a rejected value right beside the box.
    action_html = ('<span class="field-action counter-note" role="status" aria-live="polite"></span>'
                   if row.parameter in COUNTER_ROLES else '<span class="field-action"></span>')
    comment_html = f'<input type="text" class="field-comment" data-comment-for="{esc(row.parameter)}" placeholder="Comment">'
    rownum_html = f'<span class="field-rownum">{row.row_number:03d}</span>'
    return (f'<label class="field-row"{attrs}>'
            f'<span class="field-name">{rownum_html}{esc(row.parameter)}{req_mark}{tip_html}</span>'
            f'{control}{unit_html}{action_html}{comment_html}</label>')


# Lateral-scope headings as shown for a well that is not multilateral. Its
# one lateral is simply the well, so "Lateral" would only confuse; the saved
# Subcategory key is unchanged. A heading missing here shows as written.
SINGLE_WELL_HEADINGS = {"Lateral Details": "Well Details"}


def render_subcategory(category: str, subcategory: str, rows: list[ParamRow], model: dict,
                       single_well_heading: str | None = None) -> str:
    field_rows = "".join(render_field_row(r, model["param_show"], model["param_hide"]) for r in rows)
    heading = esc(subcategory)
    if single_well_heading:
        heading = (f'<span class="multi-only">{heading}</span>'
                   f'<span class="single-only">{esc(single_well_heading)}</span>')
    attrs = build_show_hide_attr(category, subcategory, model["subcat_show"], model["subcat_hide"])
    return (f'<section class="subcategory" data-category="{esc(category)}" '
            f'data-subcategory="{esc(subcategory)}"{attrs}>'
            f'<h3 class="subcat-title">{heading}</h3>'
            f'<div class="field-grid">{field_rows}</div></section>')


def render_flat_groups(grouped: dict[str, dict[str, list[ParamRow]]], model: dict,
                       single_well_headings: dict[str, str] | None = None) -> str:
    """Render subcategory sections with no category heading, in source order."""
    parts = []
    for category, subcats in grouped.items():
        for subcategory, rows in subcats.items():
            parts.append(render_subcategory(category, subcategory, rows, model,
                                            (single_well_headings or {}).get(subcategory)))
    return "".join(parts)


def render_well_section(model: dict) -> str:
    zones = []
    for category, subcats in model["well"].items():
        css_class = WELL_ZONE_CLASS.get(category, "zone-well")
        groups = "".join(render_subcategory(category, sc, rows, model) for sc, rows in subcats.items())
        zones.append(f'<section class="zone {css_class}"><h2 class="zone-title">{esc(category)}</h2>{groups}</section>')
    return f'<div id="well-section">{"".join(zones)}</div>'


def render_sand_body_template(model: dict) -> str:
    groups = render_flat_groups(model["sand_body"], model)
    return (
        '<template class="sand-body-template">'
        '<section class="interval-instance sand-body-instance">'
        '<div class="interval-banner">'
        '<h3 class="zone-title"><span class="lateral-prefix">LATERAL <span class="lateral-index"></span> - </span>'
        'COMPLETION INTERVAL <span class="completion-index"></span>'
        ' - SAND BODY <span class="interval-index"></span></h3>'
        '</div>'
        f'{groups}'
        '</section>'
        '</template>'
    )


def render_completion_template(model: dict) -> str:
    own_groups = render_flat_groups(model["completion"], model)
    sand_body_tpl = render_sand_body_template(model)
    return (
        '<template class="completion-interval-template">'
        '<section class="interval-instance completion-instance">'
        '<div class="interval-banner">'
        '<h2 class="zone-title"><span class="lateral-prefix">LATERAL <span class="lateral-index"></span> - </span>'
        'COMPLETION INTERVAL <span class="interval-index"></span></h2>'
        '</div>'
        f'<div class="own-fields">{own_groups}</div>'
        '<div class="sand-body-nest">'
        '<h3 class="nest-heading">Sand Bodies</h3>'
        '<div class="sand-bodies-container"></div>'
        '</div>'
        f'{sand_body_tpl}'
        '</section>'
        '</template>'
    )


def render_lateral_template(model: dict) -> str:
    """A well that is not multilateral shows its single lateral without the
    banner, so the form reads as before: lateral details, then intervals."""
    own_groups = render_flat_groups(model["lateral"], model, SINGLE_WELL_HEADINGS)
    completion_tpl = render_completion_template(model)
    return (
        '<template id="lateral-template">'
        '<section class="interval-instance lateral-instance">'
        '<div class="interval-banner">'
        '<h2 class="zone-title">LATERAL <span class="interval-index"></span></h2>'
        '</div>'
        f'<div class="own-fields">{own_groups}</div>'
        '<div class="completion-nest">'
        '<h2 class="nest-heading">Completion Intervals</h2>'
        '<div class="completion-intervals-container"></div>'
        '</div>'
        f'{completion_tpl}'
        '</section>'
        '</template>'
    )


CSS = """
:root {
  --header-bg: #203864; --header-text: #ffffff;
  --general-header: #ffd966; --general-row: #fff2cc;
  --well-header: #9dc3e6; --well-row: #deebf7;
  --odd-header: #a9d18e; --odd-row: #e2f0d9;
  --even-header: #f4b183; --even-row: #fbe5d6;
  --sb-odd-header: #b4a7d6; --sb-odd-row: #ede7f6;
  --sb-even-header: #ea9999; --sb-even-row: #fbe4e4;
  --lat-odd-header: #9fd8d2; --lat-odd-row: #e3f4f2;
  --lat-even-header: #d6c4b4; --lat-even-row: #f3ece6;
  --banner-text: #002060;
  --ink: #1f2328; --border: #c9c9c9;
}
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 0 0 4rem; background: #f4f4f4; color: var(--ink); }
header.page-header { background: var(--header-bg); color: var(--header-text); padding: 1.25rem 1.5rem; }
header.page-header h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
header.page-header p { margin: 0; opacity: .85; font-size: .9rem; }
header.page-header .validity-notice { margin-top: .4rem; font-weight: 600; }
header.page-header .expired-banner { margin-top: .6rem; background: #b00020; color: #fff; padding: .6rem .9rem; border-radius: 4px; font-weight: 600; opacity: 1; }
main { max-width: 1280px; margin: 1.5rem auto; padding: 0 1rem; }
.zone { margin-bottom: 1.25rem; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; }
.zone-title { margin: 0; padding: .6rem 1rem; font-size: 1.05rem; font-weight: bold; color: var(--banner-text); }
.zone-general > .zone-title { background: var(--general-header); }
.zone-well > .zone-title { background: var(--well-header); }
.subcategory { border-top: 1px solid var(--border); }
.subcat-title { margin: 0; padding: .45rem 1rem; font-size: .95rem; font-weight: bold; }
.zone-general .subcat-title { background: var(--general-header); }
.zone-well .subcat-title { background: var(--well-header); }

.lateral-instance { margin-bottom: 1.5rem; }
.lateral-instance > .interval-banner { display: none; }
#sand-form.multi-lateral .lateral-instance { border: 2px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff; }
#sand-form.multi-lateral .lateral-instance > .interval-banner { display: flex; }
#sand-form.multi-lateral .lateral-instance > .own-fields, #sand-form.multi-lateral .completion-nest { margin: 0 .75rem; }
#sand-form.multi-lateral .completion-nest { padding-bottom: .25rem; }
.lateral-instance.interval-odd > .interval-banner .zone-title { background: var(--lat-odd-header); }
.lateral-instance.interval-even > .interval-banner .zone-title { background: var(--lat-even-header); }
.lateral-instance > .own-fields { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin: .75rem 0 0; }
.lateral-instance.interval-odd > .own-fields .subcat-title { background: var(--lat-odd-header); }
.lateral-instance.interval-even > .own-fields .subcat-title { background: var(--lat-even-header); }
.lateral-instance.interval-odd > .own-fields .field-row { background: var(--lat-odd-row); }
.lateral-instance.interval-even > .own-fields .field-row { background: var(--lat-even-row); }
.lateral-prefix, .multi-only { display: none; }
#sand-form.multi-lateral .lateral-prefix, #sand-form.multi-lateral .multi-only { display: inline; }
#sand-form.multi-lateral .single-only { display: none; }
.nest-heading { margin: 1.25rem 0 .75rem; font-size: 1.1rem; }
.sand-body-nest .nest-heading { margin: 0 0 .6rem; font-size: .95rem; }

.completion-instance { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin-bottom: 1.25rem; }
.completion-instance.interval-odd > .interval-banner .zone-title { background: var(--odd-header); }
.completion-instance.interval-even > .interval-banner .zone-title { background: var(--even-header); }
.completion-instance.interval-odd > .own-fields .subcat-title { background: var(--odd-header); }
.completion-instance.interval-even > .own-fields .subcat-title { background: var(--even-header); }
.completion-instance.interval-odd > .own-fields .field-row { background: var(--odd-row); }
.completion-instance.interval-even > .own-fields .field-row { background: var(--even-row); }

.sand-body-instance { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin-bottom: 1rem; }
.sand-body-instance.interval-odd > .interval-banner .zone-title { background: var(--sb-odd-header); }
.sand-body-instance.interval-even > .interval-banner .zone-title { background: var(--sb-even-header); }
.sand-body-instance.interval-odd .subcat-title { background: var(--sb-odd-header); }
.sand-body-instance.interval-even .subcat-title { background: var(--sb-even-header); }
.sand-body-instance.interval-odd .field-row { background: var(--sb-odd-row); }
.sand-body-instance.interval-even .field-row { background: var(--sb-even-row); }

.field-grid { display: flex; flex-direction: column; }
.field-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.4fr) 220px 74px minmax(160px, 1fr); gap: .75rem; align-items: center; padding: .4rem 1rem; border-top: 1px solid #eee; }
.zone-general .field-row { background: var(--general-row); }
.zone-well .field-row { background: var(--well-row); }
.field-name { font-size: .88rem; display: flex; align-items: center; gap: .3rem; }
.field-rownum { font-family: "Consolas", monospace; font-size: .72rem; color: #888; flex: 0 0 auto; }
.field-unit { font-size: .8rem; color: #555; }
select.unit-select { width: 100%; padding: .3rem .2rem; }
.unit-toolbar { display: flex; align-items: center; gap: .65rem; margin-top: .75rem; }
.unit-toolbar select { width: auto; min-width: 8rem; }
.unit-toolbar small { opacity: .9; }
#basis-change-status { margin-top: .4rem; color: #fff4ac; font-weight: 600; }
.field-action { display: flex; }
.counter-note { font-size: .72rem; line-height: 1.2; color: #a1281c; }
.required-mark { color: #b23; font-weight: bold; }
.tt {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; border-radius: 50%; background: #8896a6; color: #fff;
  font-size: .68rem; font-weight: bold; cursor: help; position: relative; flex: 0 0 auto;
}
/* One shared tooltip, placed on the page itself by TOOLTIP_JS. Drawn inside
   a section it would be clipped by that section's overflow:hidden (which
   rounds its corners), whatever its z-index. */
#tooltip { position: fixed; z-index: 1000; max-width: 260px; background: #1f2328; color: #fff;
  padding: .4rem .6rem; border-radius: 4px; font-size: .75rem; line-height: 1.35;
  box-shadow: 0 2px 8px rgba(0,0,0,.3); pointer-events: none; }
#tooltip[hidden] { display: none; }
#tooltip::after { content: ''; position: absolute; left: var(--arrow-left, 10px); border: 5px solid transparent; }
#tooltip[data-side="above"]::after { top: 100%; border-top-color: #1f2328; }
#tooltip[data-side="below"]::after { bottom: 100%; border-bottom-color: #1f2328; }
select, input[type=text], input[type=number], input[type=date], textarea {
  width: 100%; padding: .35rem .5rem; border: 1px solid #aaa; border-radius: 4px; font: inherit; background: #fff;
}
textarea { resize: vertical; }
.multi-number { display: flex; gap: .25rem; flex-wrap: nowrap; }
.mn-item { display: flex; flex-direction: column; flex: 1 1 0; min-width: 0; }
.mn-label { font-size: .68rem; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
input.mn-input { padding: .35rem .25rem; text-align: center; }
.masked { display: flex; align-items: center; gap: .3rem; }
.masked input.mask-seg { width: calc(var(--n) * 1.15ch + 1.4rem); font-family: "Consolas", monospace; letter-spacing: .08em; text-align: center; }
.mask-lit { font-family: "Consolas", monospace; font-weight: bold; }
.interval-banner { display: flex; align-items: center; justify-content: space-between; }
.interval-banner .zone-title { flex: 1; }
.sand-body-nest { margin: .75rem 0 0; padding: .5rem 0 .75rem 1rem; border-left: 3px solid var(--border); }
.sand-bodies-container { display: flex; flex-direction: column; gap: .75rem; }
.export-bar { position: sticky; z-index: 20; bottom: 0; background: #fff; border-top: 2px solid var(--header-bg); padding: .75rem 1rem; display: flex; flex-wrap: wrap; gap: .75rem; justify-content: flex-end; max-width: 1280px; margin: 0 auto; }
#import-status { flex-basis: 100%; margin: 0; font-size: .85rem; text-align: right; }
#import-status:empty { display: none; }
.export-bar button, .file-action-menu summary { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .55rem 1.1rem; cursor: pointer; font-size: .9rem; }
.export-bar button:hover, .file-action-menu summary:hover { opacity: .9; }
.file-action-menu { position: relative; }
.file-action-menu summary { display: block; list-style: none; }
.file-action-menu summary::-webkit-details-marker { display: none; }
.file-action-options { position: absolute; right: 0; bottom: calc(100% + .35rem); min-width: 100%; padding: .35rem; display: flex; flex-direction: column; gap: .3rem; background: #fff; border: 1px solid var(--border); border-radius: 4px; box-shadow: 0 3px 8px #0002; }
.file-action-menu:not([open]) .file-action-options { display: none; }
.file-action-options button { white-space: nowrap; text-align: left; }
"""

JS = r"""
(function () {
  const SCHEMA_VERSION = __SCHEMA_VERSION__;
  // Caps per level, read from each counter's workbook max (dictionary/structure.py).
  const LIMITS = __LIMITS__;
  const MULTILATERAL = __MULTILATERAL__;
  const EXPIRES_ON = __EXPIRES_ON__;
  const EXPORT_NAME_PARAM = __EXPORT_NAME_PARAM__;
  const CHOICE_DISPLAY = __CHOICE_DISPLAY__;
  const OIL_FVF = __OIL_FVF__;
  const GAS_FVF = __GAS_FVF__;
  const UNIT_BASIS = __UNIT_BASIS__;
  const LEVEL_LABELS = { lateral: 'Lateral', completion_interval: 'Completion Interval', sand_body: 'Sand Body' };
  const wellSection = document.getElementById('well-section');
  const sandForm = document.getElementById('sand-form');
  const unitSystemSelect = document.getElementById('unit-system');
  let lastBulkSystem = 'Field';

  // Cutoff is inclusive of the whole EXPIRES_ON day in the viewer's local time --
  // the form stays usable through that date and locks starting the next day.
  if (EXPIRES_ON && new Date() > new Date(EXPIRES_ON + 'T23:59:59')) {
    document.getElementById('expired-banner').style.display = '';
    document.querySelectorAll('#sand-form input, #sand-form select, #sand-form textarea, #sand-form button')
      .forEach((el) => { el.disabled = true; });
    document.getElementById('import-btn').disabled = true;
    unitSystemSelect.disabled = true;
    document.querySelectorAll('.file-action-menu').forEach((menu) => {
      menu.open = false;
      menu.inert = true;
      menu.setAttribute('aria-disabled', 'true');
      menu.querySelectorAll('button').forEach((button) => { button.disabled = true; });
    });
    return;
  }

  // ---- block structure: Well > Lateral > Completion Interval > Sand Body ----
  function lateralBlocks() {
    return Array.from(document.querySelectorAll('#laterals-container > .lateral-instance'));
  }
  function completionBlocks(lateral) {
    return Array.from(lateral.querySelectorAll(
      ':scope > .completion-nest > .completion-intervals-container > .completion-instance'));
  }
  function sandBodyBlocks(completion) {
    return Array.from(completion.querySelectorAll(
      ':scope > .sand-body-nest > .sand-bodies-container > .sand-body-instance'));
  }
  // The fields that belong to a block itself, without its nested children.
  function ownFields(section) {
    return section.classList.contains('sand-body-instance') ? section : section.querySelector(':scope > .own-fields');
  }
  // The block (or the well section) a control or field row belongs to.
  function blockOf(el) {
    return el.closest('.interval-instance') || wellSection;
  }

  // A rule's trigger is always a field of the target's own block: Sand Body
  // 2's Fluid Type, never Sand Body 1's. Searching a parent's whole subtree
  // would return the first nested block's answer instead.
  function findParamField(root, paramName) {
    const block = root === wellSection ? wellSection :
      (root.matches('.interval-instance') ? root : blockOf(root));
    return Array.from(block.querySelectorAll(`[data-param="${CSS.escape(paramName)}"]`))
      .find((el) => blockOf(el) === block) || null;
  }
  function getControlValue(el) {
    return (el.tagName === 'SELECT' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el.value : '';
  }
  function exprMatches(block, expr) {
    return expr.split('||').some((rule) => {
      const i = rule.indexOf('=');
      const param = rule.slice(0, i);
      const value = rule.slice(i + 1);
      const trigger = findParamField(block, param);
      return trigger && getControlValue(trigger) === value;
    });
  }
  function refreshConditionalOptions(root) {
    root.querySelectorAll('select[data-options-by]').forEach((control) => {
      const config = JSON.parse(control.dataset.optionsBy);
      const [triggerName, byValue] = Object.entries(config)[0];
      const trigger = findParamField(blockOf(control), triggerName);
      const choices = byValue[trigger ? getControlValue(trigger) : ''] || [];
      const current = control.value;
      const existing = Array.from(control.options).slice(1).map((option) => option.value);
      if (JSON.stringify(existing) === JSON.stringify(choices)) return;
      const blank = new Option(control.required ? 'Select...' : '(Blank)', '');
      control.replaceChildren(blank, ...choices.map((choice) => new Option(CHOICE_DISPLAY[choice] || choice, choice)));
      control.value = choices.includes(current) ? current : '';
    });
  }
  // Numeric controls show two decimal places when unfocused. Their exact
  // value is kept separately for conversion, validation, and JSON/CSV saves;
  // focusing the control reveals the full value for accurate editing. Tiny
  // nonzero values use exponent notation instead of becoming a false 0.00.
  function exactNumber(input) { return input.dataset.exactValue ?? input.value; }
  function displayNumber(raw, input) {
    if (raw === '') return '';
    if (input.getAttribute('step') === '1') return raw; // Counts stay integers.
    const number = Number(raw);
    if (!Number.isFinite(number)) return raw;
    if (number !== 0 && Math.abs(number) < 0.005) return number.toExponential(2);
    return number.toFixed(2);
  }
  function setNumericValue(input, value) {
    const exact = String(value ?? '');
    input.dataset.exactValue = exact;
    input.value = document.activeElement === input ? exact : displayNumber(exact, input);
  }
  function clearConversionSource(input) {
    delete input.dataset.conversionSourceValue;
    delete input.dataset.conversionSourceUnit;
  }
  function clearNumericValue(input) {
    clearConversionSource(input);
    input.dataset.exactValue = '';
    input.value = '';
  }

  // ---- masked IDs, e.g. [XOM]-I-[00001] ----
  // The workbook mask ("AAA-I-#####") becomes one box per letter/digit run
  // with the fixed text between them. The saved value is the joined string,
  // so a draft keeps a half-typed ID ("XO-I-") and the API sees one value.
  function maskTokens(mask) {
    return (mask.match(/A+|#+|[^A#]+/g) || []).map((text) =>
      text[0] === 'A' || text[0] === '#' ? { slot: text[0], length: text.length } : { literal: text });
  }
  function maskSegments(control) { return Array.from(control.querySelectorAll('.mask-seg')); }
  function readMasked(control) {
    const segments = maskSegments(control).map((input) => input.value);
    if (segments.every((value) => value === '')) return null;
    let i = 0;
    return maskTokens(control.dataset.mask).map((token) => token.literal ?? segments[i++]).join('');
  }
  // The segments of a saved value, or null if it does not fit the mask
  // (a partial segment is fine; a wrong character or fixed text is not).
  function parseMasked(mask, value) {
    if (typeof value !== 'string') return null;
    const segments = [];
    let rest = value;
    for (const token of maskTokens(mask)) {
      if (token.literal !== undefined) {
        if (!rest.startsWith(token.literal)) return null;
        rest = rest.slice(token.literal.length);
      } else {
        const pattern = new RegExp('^' + (token.slot === 'A' ? '[A-Z]' : '[0-9]') + '{0,' + token.length + '}');
        const segment = rest.match(pattern)[0];
        segments.push(segment);
        rest = rest.slice(segment.length);
      }
    }
    return rest === '' ? segments : null;
  }
  function maskComplete(control) {
    return maskSegments(control).every((input) => input.value.length === input.maxLength);
  }
  function maskCode(control) {
    const first = maskSegments(control)[0];
    return first && first.dataset.slot === 'A' && maskComplete(control) ? first.value : null;
  }
  // An optional ID must be complete or blank, and a same_code_as ID must
  // share the other ID's company code. Native validity carries both, so a
  // completed export stops on the offending box with this message.
  function syncMaskValidity() {
    sandForm.querySelectorAll('[data-kind="masked"]').forEach((control) => {
      const segments = maskSegments(control);
      segments.forEach((input) => input.setCustomValidity(''));
      const filled = segments.some((input) => input.value !== '');
      if (filled && !maskComplete(control)) {
        const short = segments.find((input) => input.value.length !== input.maxLength);
        short.setCustomValidity('Complete this ID (' + control.dataset.mask + ') or leave it blank.');
        return;
      }
      const otherName = control.dataset.sameCodeAs;
      if (!otherName || !filled) return;
      const other = findParamField(blockOf(control), otherName);
      const ownCode = maskCode(control), otherCode = other && maskCode(other);
      if (ownCode && otherCode && ownCode !== otherCode) {
        segments[0].setCustomValidity('The company code must match the ' + otherName + ' (' + otherCode + ').');
      }
    });
  }
  function setMasked(control, value) {
    const segments = parseMasked(control.dataset.mask, value) || [];
    maskSegments(control).forEach((input, i) => { input.value = segments[i] || ''; });
  }
  function cleanSegment(input) {
    const cleaned = input.dataset.slot === 'A' ? input.value.toUpperCase().replace(/[^A-Z]/g, '') :
      input.value.replace(/[^0-9]/g, '');
    if (cleaned !== input.value) input.value = cleaned.slice(0, input.maxLength);
  }
  sandForm.addEventListener('keydown', (event) => {
    const input = event.target;
    if (!input.matches('.mask-seg') || event.key !== 'Backspace' || input.value !== '') return;
    const segments = maskSegments(input.closest('[data-kind="masked"]'));
    const previous = segments[segments.indexOf(input) - 1];
    if (previous) { event.preventDefault(); previous.focus(); }
  });
  sandForm.addEventListener('paste', (event) => {
    const input = event.target;
    if (!input.matches('.mask-seg')) return;
    const control = input.closest('[data-kind="masked"]');
    const text = (event.clipboardData.getData('text') || '').trim().toUpperCase();
    const segments = parseMasked(control.dataset.mask, text);
    // A whole pasted ID (XOM-I-00001) fills every box; anything else is
    // pasted into this box alone and cleaned by the input handler.
    if (!segments || !maskTokens(control.dataset.mask).some((token) => token.literal && text.includes(token.literal))) return;
    event.preventDefault();
    maskSegments(control).forEach((segment, i) => { segment.value = segments[i] || ''; });
    syncMaskValidity();
  });

  sandForm.addEventListener('input', (event) => {
    const target = event.target;
    if (target.matches('.mask-seg')) {
      cleanSegment(target);
      if (target.value.length === target.maxLength) {
        const segments = maskSegments(target.closest('[data-kind="masked"]'));
        const next = segments[segments.indexOf(target) + 1];
        if (next && document.activeElement === target) next.focus();
      }
      syncMaskValidity();
      return;
    }
    if (target.matches('input[type="number"]')) {
      // A user edit starts a new conversion chain. Unit switches in that
      // chain always use this typed value as their source, so switching back
      // restores it exactly instead of accumulating floating-point roundoff.
      clearConversionSource(target);
      target.dataset.exactValue = target.value;
      if (target.matches('[data-counter]')) {
        target.closest('.field-row').querySelector('.counter-note').textContent = '';
        refreshCounterValidity();
      }
    }
  });
  sandForm.addEventListener('focusin', (event) => {
    if (event.target.matches('input[type="number"]')) {
      event.target.value = exactNumber(event.target);
      event.target.select();
    }
  });
  sandForm.addEventListener('focusout', (event) => {
    if (event.target.matches('input[type="number"]')) {
      setNumericValue(event.target, exactNumber(event.target));
    }
  });
  function clearControl(control) {
    if (control.dataset.kind === 'multi_number') {
      control.querySelectorAll('input').forEach(clearNumericValue);
      return;
    }
    if (control.dataset.kind === 'masked') { maskSegments(control).forEach((input) => { input.value = ''; }); return; }
    if (control.dataset.kind === 'number') { clearNumericValue(control); return; }
    control.value = '';
  }
  // A hidden field/subcategory must not leave a stale value behind -- otherwise
  // a trigger no longer shown (e.g. the "OH ..." selector after switching
  // Completion Type to Cased Hole) keeps counting toward some other field's
  // show/hide decision even though the user can no longer see or change it.
  function resetHiddenControls(el) {
    el.querySelectorAll('[data-param]').forEach(clearControl);
    // Bo/Bg are alternatives for one physical measurement. A comment on
    // the old alternative must not survive a Fluid Type change under a
    // misleading parameter name.
    const rows = el.classList.contains('field-row') ? [el] : Array.from(el.querySelectorAll('.field-row'));
    rows.forEach((row) => {
      if ([OIL_FVF, GAS_FVF].includes(fieldParam(row))) row.querySelector('.field-comment').value = '';
    });
  }
  // Hiding a control with CSS does NOT exempt it from constraint validation --
  // only `disabled` does. Without this, a required field the user can't even see
  // (for example, the required offshore Water depth field on an Onshore
  // record) keeps failing reportValidity() forever. Because the browser can't
  // focus an unrendered control to show its message, exports die silently.
  // So the same pass that hides a field also disables its controls, and
  // re-enables them when the field comes back.
  //
  // Hidden-ness must be read from the whole ancestor chain rather than the
  // element's own style: a field row can have its own satisfied show-if rule
  // while the parent section is hidden by an unrelated answer. In that case
  // the row still has display:'' but remains unreachable.
  function isRuleHidden(el) {
    for (let node = el; node; node = node.parentElement) {
      if (node.style && node.style.display === 'none') return true;
    }
    return false;
  }
  // Buttons are deliberately excluded: they're barred from constraint
  // validation anyway.
  function syncValidationExemptions(root) {
    root.querySelectorAll('input, select, textarea').forEach((control) => {
      control.disabled = isRuleHidden(control);
    });
  }
  // Each rule is matched against its own block's answers (see findParamField),
  // so evaluating a parent's subtree also refreshes its nested blocks correctly.
  function evaluateVisibility(root) {
    refreshConditionalOptions(root);
    root.querySelectorAll('[data-show-if], [data-hide-if]').forEach((el) => {
      const block = blockOf(el);
      let visible = true;
      const showExpr = el.getAttribute('data-show-if');
      if (showExpr) visible = exprMatches(block, showExpr);
      const hideExpr = el.getAttribute('data-hide-if');
      if (visible && hideExpr && exprMatches(block, hideExpr)) visible = false;
      el.style.display = visible ? '' : 'none';
      if (!visible) resetHiddenControls(el);
    });
    // Only correct once every display above has settled, since an exemption
    // depends on the element's ancestors, not just on the element itself.
    syncValidationExemptions(root);
  }

  // Unit choices convert within one production basis. Liquid-to-gas is a new
  // measurement, not a relabeling, so the basis comes from Well type or Fluid
  // Type (see syncBasisUnits) and the user picks only Field or SI within it.
  function unitChoices(select) { return JSON.parse(select.dataset.unitChoices); }
  function unitChoice(select, unit) { return unitChoices(select).find((choice) => choice.unit === unit); }
  function fieldUnit(row) {
    const el = row.querySelector('.field-unit');
    return el?.tagName === 'SELECT' ? el.value : (el?.dataset.unit || null);
  }
  function updateUnitLimits(row, choice, choices) {
    const input = row.querySelector('input[data-kind="number"]');
    if (!input) return;
    if (input.dataset.fieldMin === undefined) input.dataset.fieldMin = input.getAttribute('min') ?? '';
    if (input.dataset.fieldMax === undefined) input.dataset.fieldMax = input.getAttribute('max') ?? '';
    const source = choices[0];
    for (const [attr, raw] of [['min', input.dataset.fieldMin], ['max', input.dataset.fieldMax]]) {
      if (raw === '') { input.removeAttribute(attr); continue; }
      if (source.group !== choice.group) {
        // A zero minimum is basis-independent: negative rates/PI are invalid
        // whether the user chose liquid or gas. Other bounds cannot transfer.
        if (Number(raw) === 0) input.setAttribute(attr, '0');
        else input.removeAttribute(attr);
        continue;
      }
      const canonical = Number(raw) * source.scale + source.offset;
      input.setAttribute(attr, String((canonical - choice.offset) / choice.scale));
    }
  }
  function setFieldUnit(select, nextUnit) {
    const oldUnit = select.dataset.currentUnit;
    if (oldUnit === nextUnit) return true;
    const before = unitChoice(select, oldUnit), after = unitChoice(select, nextUnit);
    if (!before || !after) return false;
    const row = select.closest('.field-row');
    const controls = Array.from(row.querySelectorAll('input[data-kind="number"], .mn-input'));
    const filled = controls.filter((input) => exactNumber(input) !== '');
    if (before.group !== after.group) {
      filled.forEach(clearNumericValue);
    } else if (filled.length) {
      filled.forEach((input) => {
        if (!input.dataset.conversionSourceUnit) {
          input.dataset.conversionSourceUnit = oldUnit;
          input.dataset.conversionSourceValue = exactNumber(input);
        }
        const sourceUnit = input.dataset.conversionSourceUnit;
        const sourceValue = input.dataset.conversionSourceValue;
        if (nextUnit === sourceUnit) {
          // Preserve the exact digits the user entered, including trailing
          // zeros, after any number of Field/SI switches.
          setNumericValue(input, sourceValue);
        } else {
          const source = unitChoice(select, sourceUnit);
          const canonical = Number(sourceValue) * source.scale + source.offset;
          const converted = (canonical - after.offset) / after.scale;
          setNumericValue(input, Number(converted.toPrecision(15)).toString());
        }
      });
    }
    select.value = nextUnit;
    select.dataset.currentUnit = nextUnit;
    if (after.system === 'Field' || after.system === 'both') select.dataset.lastFieldUnit = nextUnit;
    updateUnitLimits(row, after, unitChoices(select));
    return true;
  }
  function preferredUnit(select, system) {
    const choices = unitChoices(select);
    const current = unitChoice(select, select.dataset.currentUnit);
    const group = current.group;
    if (system === 'Field') {
      const remembered = choices.find((choice) => choice.unit === select.dataset.lastFieldUnit && choice.group === group);
      if (remembered && remembered.system !== 'SI') return remembered.unit;
    }
    return (choices.find((choice) => choice.group === group &&
      (choice.system === system || choice.system === 'both')) || choices[0]).unit;
  }
  // Well type decides liquid vs gas for well-level rates and PI. A Sand Body's
  // PI follows its own Fluid Type, or Well type while Fluid Type is blank.
  function basisForAnswers(driver, answer, wellType) {
    return UNIT_BASIS[driver][answer] || UNIT_BASIS['Well type'][wellType] || 'liquid';
  }
  function basisFor(select) {
    const driver = select.dataset.unitBasis;
    const root = select.closest('.sand-body-instance') || wellSection;
    return basisForAnswers(driver, findParamField(root, driver)?.value,
      findParamField(wellSection, 'Well type').value);
  }
  // Offer only the current basis's units. A number entered in the other basis
  // measured a different production stream and cannot be converted, so it is
  // cleared; the returned count lets the caller tell the user.
  function syncBasisUnits(root) {
    let cleared = 0;
    root.querySelectorAll('select[data-unit-basis]').forEach((select) => {
      const basis = basisFor(select);
      Array.from(select.options).forEach((option) => {
        option.hidden = option.disabled = unitChoice(select, option.value).group !== basis;
      });
      const current = unitChoice(select, select.dataset.currentUnit);
      if (current.group === basis) return;
      select.closest('.field-row').querySelectorAll('input[type="number"]').forEach((input) => {
        if (exactNumber(input) !== '') cleared += 1;
      });
      const target = unitChoices(select).find((choice) => choice.group === basis &&
        (choice.system === current.system || choice.system === 'both'));
      setFieldUnit(select, target.unit);
    });
    updateTopUnitIndicator();
    return cleared;
  }
  function reportBasisChange(driver, cleared) {
    const message = cleared ?
      `Changing ${driver} cleared ${cleared} liquid/gas measurement(s). Re-enter them in the new basis.` : '';
    document.getElementById('basis-change-status').textContent = message;
    // Rare, but a silently emptied field is easy to miss further down the form.
    if (cleared) alert(message);
  }
  function applyBulkUnits(root, system) {
    root.querySelectorAll('select.unit-select').forEach((select) => {
      setFieldUnit(select, preferredUnit(select, system));
    });
  }
  function updateTopUnitIndicator() {
    const selectors = Array.from(sandForm.querySelectorAll('select.unit-select'));
    const systems = selectors.map((select) => unitChoice(select, select.dataset.currentUnit).system);
    const field = systems.every((system) => system === 'Field' || system === 'both');
    const si = systems.every((system) => system === 'SI' || system === 'both');
    unitSystemSelect.value = field && si ? lastBulkSystem : (field ? 'Field' : (si ? 'SI' : 'Custom'));
  }
  unitSystemSelect.addEventListener('change', () => {
    lastBulkSystem = unitSystemSelect.value;
    applyBulkUnits(sandForm, lastBulkSystem);
    updateTopUnitIndicator();
  });

  // ---- repeaters: one counter per level is the only control ----
  function makeRepeater({ container, template, level, onAdd }) {
    const repeater = {
      level,
      get count() { return container.children.length; },
      blocks() { return Array.from(container.children); },
      add() {
        if (repeater.count >= LIMITS[level]) return null;
        const node = template.content.cloneNode(true);
        const section = node.querySelector('.interval-instance');
        applyBulkUnits(section, lastBulkSystem);
        container.appendChild(node);
        if (onAdd) onAdd(section);
        relabel();
        evaluateVisibility(section);
        syncBasisUnits(section);
        return section;
      },
      removeLast() {
        if (repeater.count <= 1) return;
        container.lastElementChild.remove();
        relabel();
      },
      setCount(n) {
        while (repeater.count > n && repeater.count > 1) repeater.removeLast();
        while (repeater.count < n) repeater.add();
      },
    };
    return repeater;
  }
  function wireCompletion(completion) {
    completion.sandBodyRepeater = makeRepeater({
      container: completion.querySelector(':scope > .sand-body-nest > .sand-bodies-container'),
      template: completion.querySelector(':scope > .sand-body-template'),
      level: 'sand_body',
    });
    completion.sandBodyRepeater.add();
  }
  function wireLateral(lateral) {
    lateral.completionRepeater = makeRepeater({
      container: lateral.querySelector(':scope > .completion-nest > .completion-intervals-container'),
      template: lateral.querySelector(':scope > .completion-interval-template'),
      level: 'completion_interval',
      onAdd: wireCompletion,
    });
    lateral.completionRepeater.add();
  }
  const lateralRepeater = makeRepeater({
    container: document.getElementById('laterals-container'),
    template: document.getElementById('lateral-template'),
    level: 'lateral',
    onAdd: wireLateral,
  });
  // Numbers and odd/even colors are recomputed from the DOM after any change,
  // so every banner names its full path (Lateral 2 - Completion Interval 1 -
  // Sand Body 3) and each level's colors restart inside its parent.
  function setBlockIndex(section, n) {
    section.classList.remove('interval-odd', 'interval-even');
    section.classList.add(n % 2 === 1 ? 'interval-odd' : 'interval-even');
    section.dataset.intervalIndex = n;
    const banner = section.querySelector(':scope > .interval-banner');
    banner.querySelector('.interval-index').textContent = n;
    return banner;
  }
  function relabel() {
    lateralBlocks().forEach((lateral, i) => {
      setBlockIndex(lateral, i + 1);
      completionBlocks(lateral).forEach((completion, j) => {
        setBlockIndex(completion, j + 1).querySelector('.lateral-index').textContent = i + 1;
        sandBodyBlocks(completion).forEach((sandBody, k) => {
          const banner = setBlockIndex(sandBody, k + 1);
          banner.querySelector('.lateral-index').textContent = i + 1;
          banner.querySelector('.completion-index').textContent = j + 1;
        });
      });
    });
  }
  function repeaterFor(level, row) {
    if (level === 'lateral') return lateralRepeater;
    if (level === 'completion_interval') return row.closest('.lateral-instance').completionRepeater;
    return row.closest('.completion-instance').sandBodyRepeater;
  }
  // Counters are structure, not data: a block holding only its prefilled
  // child counter is still empty.
  function blockHasData(section) {
    return Array.from(section.querySelectorAll('.field-row')).some((row) =>
      !row.querySelector('[data-counter]') &&
      (readFieldValue(row) !== null || row.querySelector('.field-comment').value !== ''));
  }
  function rangeText(label, from, to) {
    return from === to ? `${label} ${from}` : `${label}s ${from}–${to}`;
  }
  // Removing blocks deletes what was typed in them, so ask first whenever any
  // of them has data. The list of affected blocks names exactly what goes.
  function confirmRemoval(repeater, keep, reason) {
    const doomed = repeater.blocks().slice(keep);
    if (!doomed.some(blockHasData)) return true;
    return window.confirm(`${reason} deletes ${rangeText(LEVEL_LABELS[repeater.level], keep + 1, repeater.count)} ` +
      'and everything entered in them. Continue?');
  }
  // A completed export must not say "3" while 2 blocks exist. A counter only
  // differs from its blocks while it is being typed in (leaving the box
  // applies it), so this is a safety net; drafts save it as typed.
  function refreshCounterValidity() {
    sandForm.querySelectorAll('[data-counter]').forEach((input) => {
      const raw = exactNumber(input);
      const count = repeaterFor(input.dataset.counter, input.closest('.field-row')).count;
      input.setCustomValidity(raw !== '' && Number(raw) !== count ?
        `${raw} entered but ${count} shown: leave this box to update the blocks.` : '');
    });
  }
  // A counter takes effect when you leave it, press Enter, or click its
  // arrows -- not on every keystroke, or typing "12" would first build 1
  // block. Blank changes nothing (the required check covers it on export).
  // A value outside the workbook's range is put back to the current count
  // with a note beside the box; removing blocks that hold data asks first.
  // Safe to call repeatedly: a value that already matches its blocks changes
  // nothing, so leaving the box after a change or Enter is harmless.
  function applyCounter(input) {
    const row = input.closest('.field-row');
    const note = row.querySelector('.counter-note');
    const repeater = repeaterFor(input.dataset.counter, row);
    const raw = exactNumber(input);
    const keepShown = () => setNumericValue(input, repeater.count >= Number(input.min || 1) ? String(repeater.count) : '');
    if (raw === '' || raw === String(repeater.count)) { refreshCounterValidity(); return; }
    note.textContent = '';
    input.setCustomValidity('');
    input.value = raw;
    const n = Number(raw);
    if (!input.checkValidity()) {
      note.textContent = `Use a whole number from ${input.min} to ${input.max}.`;
      keepShown();
      refreshCounterValidity();
      return;
    }
    if (n < repeater.count && !confirmRemoval(repeater, n, `Reducing ${fieldParam(row)} to ${n}`)) {
      keepShown();
      refreshCounterValidity();
      return;
    }
    repeater.setCount(n);
    setNumericValue(input, String(n));
    refreshCounterValidity();
    updateTopUnitIndicator();
  }
  sandForm.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.matches('[data-counter]')) {
      event.preventDefault();
      applyCounter(event.target);
      // Blocking Enter's default also skips the browser's own "committed"
      // mark, so its arrows would not fire a change when stepping back to
      // the value the box had on entry. Leaving and re-entering resets it.
      event.target.blur();
      event.target.focus();
    }
  });
  // The browser does not fire a change in every case (above), so leaving
  // the box always applies it as well.
  sandForm.addEventListener('focusout', (event) => {
    if (event.target.matches('[data-counter]')) applyCounter(event.target);
  });
  // A well that is not multilateral is its main bore alone: Lateral 1, shown
  // without a lateral banner. Turning the answer away from Yes removes the
  // other laterals (after confirming if they hold data).
  function multilateralControl() { return findParamField(wellSection, MULTILATERAL); }
  function syncLateralMode() {
    sandForm.classList.toggle('multi-lateral', multilateralControl().value === 'Yes');
  }
  function leaveMultilateral(control) {
    if (control.value === 'Yes' || lateralRepeater.count <= 1) return true;
    if (!confirmRemoval(lateralRepeater, 1, `Changing "${MULTILATERAL}" to ${control.value || 'blank'}`)) {
      control.value = 'Yes';
      return false;
    }
    lateralRepeater.setCount(1);
    return true;
  }

  sandForm.addEventListener('change', (event) => {
    const target = event.target;
    if (target.matches('[data-counter]')) applyCounter(target);
    if (target.dataset.param === MULTILATERAL) leaveMultilateral(target);
    evaluateVisibility(blockOf(target));
    if (target.dataset.param === MULTILATERAL) syncLateralMode();
    if (target.dataset.param === 'Well type') {
      reportBasisChange('Well type', syncBasisUnits(sandForm));
    } else if (target.dataset.param === 'Fluid Type') {
      reportBasisChange('Fluid Type', syncBasisUnits(target.closest('.sand-body-instance')));
    } else if (target.matches('select.unit-select')) {
      setFieldUnit(target, target.value);
    }
    refreshCounterValidity();
    syncMaskValidity();
    updateTopUnitIndicator();
  });

  evaluateVisibility(wellSection);
  lateralRepeater.add();
  syncBasisUnits(wellSection);
  syncLateralMode();
  refreshCounterValidity();
  syncMaskValidity();
  updateTopUnitIndicator();

  // ---- collect a shared record for both file formats ----
  function readFieldValue(fieldRow) {
    const control = fieldRow.querySelector('[data-kind]');
    if (!control) return null;
    if (control.dataset.kind === 'multi_number') {
      const vals = Array.from(control.querySelectorAll('input')).map(exactNumber);
      return vals.every((v) => v === '') ? null : vals;
    }
    if (control.dataset.kind === 'masked') return readMasked(control);
    const value = control.dataset.kind === 'number' ? exactNumber(control) : control.value;
    return value === '' ? null : value;
  }

  function fieldParam(fieldRow) {
    const control = fieldRow.querySelector('[data-param]');
    return control ? control.getAttribute('data-param') : '';
  }

  function walkFields(root, visibleOnly, cb) {
    if (!root) return;
    root.querySelectorAll('.subcategory').forEach((sub) => {
      if (visibleOnly && sub.style.display === 'none') return;
      sub.querySelectorAll('.field-row').forEach((fr) => {
        if (visibleOnly && fr.style.display === 'none') return;
        cb(sub, fr);
      });
    });
  }

  function putBucketValue(bucket, category, subcategory, parameter, value) {
    bucket[category] = bucket[category] || {};
    bucket[category][subcategory] = bucket[category][subcategory] || {};
    bucket[category][subcategory][parameter] = value;
  }

  function bucketValue(bucket, category, subcategory, parameter) {
    return bucket?.[category]?.[subcategory]?.[parameter] ?? null;
  }

  function findBucketParamValue(bucket, parameter) {
    for (const subcategories of Object.values(bucket || {})) {
      for (const parameters of Object.values(subcategories)) {
        if (Object.hasOwn(parameters, parameter)) {
          const value = parameters[parameter];
          return isObject(value) ? value.value : value;
        }
      }
    }
    return null;
  }

  function collectBucket(root) {
    const bucket = {};
    // An explicit unit is part of the state even if a field is blank or
    // temporarily hidden. Hidden answers are still omitted.
    walkFields(root, false, (sub, fr) => {
      // Bo and Bg are two exclusive representations of the same workbook
      // slot. Do not serialize the hidden alternative's empty unit choice.
      if (isRuleHidden(fr) && [OIL_FVF, GAS_FVF].includes(fieldParam(fr))) return;
      const unit = fieldUnit(fr);
      const value = isRuleHidden(fr) ? null : readFieldValue(fr);
      if (unit !== null || value !== null) {
        putBucketValue(bucket, sub.dataset.category, sub.dataset.subcategory,
          fieldParam(fr), unit === null ? value : { value, unit });
      }
    });
    return bucket;
  }

  function collectComments(root) {
    const bucket = {};
    // A comment remains in the form if its conditional field is hidden, so
    // save it even though hidden field values are cleared by visibility rules.
    walkFields(root, false, (sub, fr) => {
      if (isRuleHidden(fr) && [OIL_FVF, GAS_FVF].includes(fieldParam(fr))) return;
      const comment = fr.querySelector('.field-comment').value;
      if (comment !== '') putBucketValue(bucket, sub.dataset.category, sub.dataset.subcategory, fieldParam(fr), comment);
    });
    return bucket;
  }

  function collectData() {
    const comments = { well: collectComments(wellSection), laterals: [] };
    const laterals = lateralBlocks().map((lateral) => {
      const note = { fields: collectComments(ownFields(lateral)), completion_intervals: [] };
      comments.laterals.push(note);
      return {
        fields: collectBucket(ownFields(lateral)),
        completion_intervals: completionBlocks(lateral).map((completion) => {
          const sandBodies = sandBodyBlocks(completion);
          note.completion_intervals.push({ fields: collectComments(ownFields(completion)),
            sand_bodies: sandBodies.map(collectComments) });
          return { fields: collectBucket(ownFields(completion)), sand_bodies: sandBodies.map(collectBucket) };
        }),
      };
    });
    return { schema_version: SCHEMA_VERSION, generated_at: new Date().toISOString(),
      well: collectBucket(wellSection), laterals, comments };
  }

  // Long CSV layout: one row per field, with the block it belongs to in the
  // Lateral / Completion Interval / Sand Body columns. Structural rows (Row
  // Type) keep blank blocks and the timestamp.
  const CSV_HEADER = ['Category', 'Subcategory', 'Parameter', 'Lateral', 'Completion Interval', 'Sand Body',
    'Value', 'Unit', 'Comment', 'Row Type'];

  function collectCsvRows(record) {
    const rows = [
      ['', '', 'schema_version', '', '', '', record.schema_version, '', '', 'metadata'],
      ['', '', 'generated_at', '', '', '', record.generated_at, '', '', 'metadata'],
      ['', '', 'record_status', '', '', '', record.record_status, '', '', 'metadata'],
    ];
    function pushFields(root, values, comments, path) {
      walkFields(root, false, (sub, fr) => {
        const category = sub.dataset.category, subcategory = sub.dataset.subcategory, parameter = fieldParam(fr);
        const value = bucketValue(values, category, subcategory, parameter);
        const comment = bucketValue(comments, category, subcategory, parameter);
        if (value === null && comment === null) return;
        const bare = isObject(value) ? value.value : value;
        const unit = isObject(value) ? value.unit : '';
        rows.push([category, subcategory, parameter, ...path,
          Array.isArray(bare) ? JSON.stringify(bare) : (bare ?? ''),
          unit, comment ?? '', 'field']);
      });
    }
    pushFields(wellSection, record.well, record.comments.well, ['', '', '']);
    lateralBlocks().forEach((lateral, i) => {
      const l = String(i + 1), data = record.laterals[i], notes = record.comments.laterals[i];
      rows.push(['', '', '', l, '', '', '', '', '', 'lateral']);
      pushFields(ownFields(lateral), data.fields, notes.fields, [l, '', '']);
      completionBlocks(lateral).forEach((completion, j) => {
        const c = String(j + 1), comp = data.completion_intervals[j], compNotes = notes.completion_intervals[j];
        rows.push(['', '', '', l, c, '', '', '', '', 'completion_interval']);
        pushFields(ownFields(completion), comp.fields, compNotes.fields, [l, c, '']);
        sandBodyBlocks(completion).forEach((sandBody, k) => {
          const s = String(k + 1);
          rows.push(['', '', '', l, c, s, '', '', '', 'sand_body']);
          pushFields(sandBody, comp.sand_bodies[k], compNotes.sand_bodies[k], [l, c, s]);
        });
      });
    });
    return rows;
  }

  function toCsv(rows) {
    const quote = (value) => '"' + String(value).replace(/"/g, '""') + '"';
    return [CSV_HEADER, ...rows].map((row) => row.map(quote).join(',')).join('\r\n');
  }

  function parseCsv(text) {
    const source = text.replace(/^﻿/, '');
    const rows = [], row = [];
    let cell = '', quoted = false;
    for (let i = 0; i < source.length; i += 1) {
      const ch = source[i];
      if (quoted) {
        if (ch === '"' && source[i + 1] === '"') { cell += '"'; i += 1; }
        else if (ch === '"') quoted = false;
        else cell += ch;
      } else if (ch === '"') {
        if (cell !== '') throw new Error('Malformed CSV quoting.');
        quoted = true;
      } else if (ch === ',') {
        row.push(cell); cell = '';
      } else if (ch === '\r' || ch === '\n') {
        row.push(cell); cell = '';
        rows.push(row.splice(0));
        if (ch === '\r' && source[i + 1] === '\n') i += 1;
      } else {
        cell += ch;
      }
    }
    if (quoted) throw new Error('Unclosed quoted CSV cell.');
    if (row.length || cell !== '') { row.push(cell); rows.push(row); }
    return rows;
  }

  // Field roots of the first block at each level. Every level always has at
  // least one block, and all blocks of a level share the same fields.
  function templateRoots() {
    const lateral = lateralBlocks()[0];
    const completion = completionBlocks(lateral)[0];
    return { lateral: ownFields(lateral), completion: ownFields(completion), sandBody: sandBodyBlocks(completion)[0] };
  }

  function csvToData(text) {
    const rows = parseCsv(text);
    if (!rows.length || rows[0].join('\0') !== CSV_HEADER.join('\0')) {
      throw new Error('CSV columns do not match this form.');
    }
    const record = { schema_version: null, generated_at: null, record_status: null,
      well: {}, laterals: [], comments: { well: {}, laterals: [] } };
    const roots = templateRoots();

    function index(value, level) {
      const n = Number(value);
      if (!/^[1-9]\d*$/.test(value) || n > LIMITS[level]) {
        throw new Error('Invalid ' + LEVEL_LABELS[level] + ' index: ' + value);
      }
      return n - 1;
    }
    function lateralAt(raw) {
      const i = index(raw, 'lateral');
      while (record.laterals.length <= i) {
        record.laterals.push({ fields: {}, completion_intervals: [] });
        record.comments.laterals.push({ fields: {}, completion_intervals: [] });
      }
      return [record.laterals[i], record.comments.laterals[i]];
    }
    function completionAt(lRaw, cRaw) {
      const [lateral, notes] = lateralAt(lRaw);
      const j = index(cRaw, 'completion_interval');
      while (lateral.completion_intervals.length <= j) {
        lateral.completion_intervals.push({ fields: {}, sand_bodies: [] });
        notes.completion_intervals.push({ fields: {}, sand_bodies: [] });
      }
      return [lateral.completion_intervals[j], notes.completion_intervals[j]];
    }
    function sandBodyAt(lRaw, cRaw, sRaw) {
      const [completion, notes] = completionAt(lRaw, cRaw);
      const k = index(sRaw, 'sand_body');
      while (completion.sand_bodies.length <= k) {
        completion.sand_bodies.push({});
        notes.sand_bodies.push({});
      }
      return [completion.sand_bodies[k], notes.sand_bodies[k]];
    }

    for (const row of rows.slice(1)) {
      if (row.length !== CSV_HEADER.length) throw new Error('CSV row has the wrong number of columns.');
      const [category, subcategory, parameter, lRaw, cRaw, sRaw, value, unit, comment, type] = row;
      if (type === 'metadata') {
        if (parameter === 'schema_version') {
          if (!/^(0|[1-9]\d*)$/.test(value)) throw new Error('Invalid schema version in CSV.');
          record.schema_version = Number(value);
        }
        else if (parameter === 'generated_at') record.generated_at = value;
        else if (parameter === 'record_status') record.record_status = value;
        else throw new Error('Unknown CSV metadata: ' + parameter);
        continue;
      }
      if (type === 'lateral') { lateralAt(lRaw); continue; }
      if (type === 'completion_interval') { completionAt(lRaw, cRaw); continue; }
      if (type === 'sand_body') { sandBodyAt(lRaw, cRaw, sRaw); continue; }
      if (type !== 'field') throw new Error('Unknown CSV row type: ' + type);
      if ((sRaw !== '' && cRaw === '') || (cRaw !== '' && lRaw === '')) {
        throw new Error('A CSV row names a block without its parent: ' + parameter);
      }
      let values = record.well, comments = record.comments.well, root = wellSection;
      if (sRaw !== '') {
        const [bucket, notes] = sandBodyAt(lRaw, cRaw, sRaw);
        values = bucket; comments = notes; root = roots.sandBody;
      } else if (cRaw !== '') {
        const [completion, notes] = completionAt(lRaw, cRaw);
        values = completion.fields; comments = notes.fields; root = roots.completion;
      } else if (lRaw !== '') {
        const [lateral, notes] = lateralAt(lRaw);
        values = lateral.fields; comments = notes.fields; root = roots.lateral;
      }
      const fieldRow = findFieldRow(root, category, subcategory, parameter);
      if (!fieldRow) throw new Error('Unknown CSV field: ' + parameter);
      const unitElement = fieldRow.querySelector('.field-unit');
      const choices = unitElement.tagName === 'SELECT' ? unitChoices(unitElement).map((choice) => choice.unit) :
        (unitElement.dataset.unit ? [unitElement.dataset.unit] : []);
      if (choices.length && !choices.includes(unit)) throw new Error('Unknown unit for ' + parameter + '.');
      if (!choices.length && unit !== '') throw new Error('Unexpected unit for ' + parameter + '.');
      const control = fieldRow.querySelector('[data-kind]');
      const parsed = value === '' ? null : (control.dataset.kind === 'multi_number' ? JSON.parse(value) : value);
      if (choices.length || parsed !== null) {
        if (bucketValue(values, category, subcategory, parameter) !== null) throw new Error('Duplicate CSV field: ' + parameter);
        putBucketValue(values, category, subcategory, parameter,
          choices.length ? { value: parsed, unit } : parsed);
      }
      if (comment !== '') putBucketValue(comments, category, subcategory, parameter, comment);
    }
    return record;
  }

  function findFieldRow(root, category, subcategory, parameter) {
    for (const sub of root.querySelectorAll('.subcategory')) {
      if (sub.dataset.category !== category || sub.dataset.subcategory !== subcategory) continue;
      for (const fieldRow of sub.querySelectorAll('.field-row')) {
        if (fieldParam(fieldRow) === parameter) return fieldRow;
      }
    }
    return null;
  }

  function isObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  // Same rule as the API: a real calendar date written YYYY-MM-DD.
  function isIsoDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const parsed = new Date(value + 'T00:00:00Z');
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
  }

  function validateBucket(bucket, root, commentsOnly, wellType) {
    if (!isObject(bucket)) throw new Error('A field group is not an object.');
    for (const [category, subcategories] of Object.entries(bucket)) {
      if (!isObject(subcategories)) throw new Error('Invalid subcategory in ' + category + '.');
      for (const [subcategory, parameters] of Object.entries(subcategories)) {
        if (!isObject(parameters)) throw new Error('Invalid fields in ' + subcategory + '.');
        for (const [parameter, value] of Object.entries(parameters)) {
          const row = findFieldRow(root, category, subcategory, parameter);
          if (!row) throw new Error('Field is not in this form: ' + parameter);
          if (commentsOnly) {
            if (typeof value !== 'string') throw new Error('Comment must be text: ' + parameter);
            continue;
          }
          const unitElement = row.querySelector('.field-unit');
          const driver = unitElement.dataset.unitBasis;
          const basis = driver && basisForAnswers(driver, findBucketParamValue(bucket, driver), wellType);
          const allowedUnits = unitElement.tagName === 'SELECT' ?
            unitChoices(unitElement).filter((choice) => !basis || choice.group === basis)
              .map((choice) => choice.unit) :
            (unitElement.dataset.unit ? [unitElement.dataset.unit] : []);
          if (allowedUnits.length) {
            if (!isObject(value) || !Object.hasOwn(value, 'value') ||
                !Object.hasOwn(value, 'unit') || !allowedUnits.includes(value.unit)) {
              throw new Error('Invalid value or unit for ' + parameter + '.');
            }
          } else if (isObject(value)) {
            throw new Error('Unexpected unit for ' + parameter + '.');
          }
          const bare = allowedUnits.length ? value.value : value;
          if (bare === null) continue;  // An empty measurement still has a saved unit.
          const control = row.querySelector('[data-kind]');
          if (control.dataset.kind === 'multi_number') {
            if (!Array.isArray(bare) || bare.length !== control.querySelectorAll('input').length ||
                bare.some((v) => typeof v !== 'string' && typeof v !== 'number')) {
              throw new Error('Invalid multi-value field: ' + parameter);
            }
          } else if (typeof bare !== 'string' && typeof bare !== 'number') {
            throw new Error('Invalid field value: ' + parameter);
          } else if (control.dataset.kind === 'date' && !isIsoDate(String(bare))) {
            // A date input silently discards any other text, so an import
            // would "succeed" with the date missing. Excel rewrites CSV dates
            // in the viewer's locale (1/10/2024 or 10/1/2024) when it re-saves
            // a file; refuse rather than guess month vs day order.
            throw new Error('Invalid date for ' + parameter + ': "' + bare +
              '". Dates must be YYYY-MM-DD. If the CSV was opened and saved in Excel, ' +
              're-enter the date in that format or use the original file.');
          } else if (control.dataset.kind === 'masked' && !parseMasked(control.dataset.mask, bare)) {
            throw new Error('Invalid ' + parameter + ': "' + bare + '". Expected the format ' +
              control.dataset.mask + ' (A = capital letter, # = digit).');
          } else if (control.tagName === 'SELECT') {
            let options = Array.from(control.options).map((option) => option.value);
            if (control.dataset.optionsBy) {
              const config = JSON.parse(control.dataset.optionsBy);
              const [triggerName, byValue] = Object.entries(config)[0];
              options = byValue[findBucketParamValue(bucket, triggerName)] || [];
            }
            if (!options.includes(String(bare))) throw new Error('Unknown option for ' + parameter + '.');
          }
        }
      }
    }
    if (!commentsOnly) {
      const fvf = bucket?.['Reservoir Characterization']?.['Reservoir Rock and Fluid Properties'];
      if (fvf) {
        const gas = ['Condensate', 'Wet Gas', 'Dry Gas'].includes(fvf['Fluid Type']);
        const inactive = gas ? OIL_FVF : GAS_FVF;
        const old = fvf[inactive];
        const bare = isObject(old) ? old.value : old;
        if (bare !== undefined && bare !== null && bare !== '') {
          throw new Error('The saved ' + inactive + ' conflicts with Fluid Type.');
        }
      }
    }
  }

  function checkBlockList(list, level) {
    if (!Array.isArray(list) || list.length < 1 || list.length > LIMITS[level]) {
      throw new Error('Expected 1 to ' + LIMITS[level] + ' ' + LEVEL_LABELS[level] + 's.');
    }
  }
  function checkSameLength(notes, blocks, level) {
    if (!Array.isArray(notes) || notes.length !== blocks.length) {
      throw new Error('Comment groups do not match ' + LEVEL_LABELS[level] + 's.');
    }
  }

  function validateImport(record) {
    if (!isObject(record) || record.schema_version !== SCHEMA_VERSION) {
      throw new Error('Unsupported or missing schema version. Expected ' + SCHEMA_VERSION + '.');
    }
    if (record.record_status != null &&
        record.record_status !== 'draft' && record.record_status !== 'complete') {
      throw new Error('Unknown file status.');
    }
    checkBlockList(record.laterals, 'lateral');
    if (findBucketParamValue(record.well, MULTILATERAL) !== 'Yes' && record.laterals.length !== 1) {
      throw new Error('A well that is not multilateral must have exactly one lateral.');
    }
    const roots = templateRoots();
    const wellType = findBucketParamValue(record.well, 'Well type');
    validateBucket(record.well, wellSection, false, wellType);
    const comments = record.comments ?? { well: {}, laterals: record.laterals.map((lateral) => ({
      fields: {}, completion_intervals: (lateral?.completion_intervals || []).map((comp) => ({
        fields: {}, sand_bodies: (comp?.sand_bodies || []).map(() => ({})) })) })) };
    if (!isObject(comments)) throw new Error('Comments are not an object.');
    validateBucket(comments.well, wellSection, true);
    checkSameLength(comments.laterals, record.laterals, 'lateral');
    record.laterals.forEach((lateral, i) => {
      const lateralNotes = comments.laterals[i];
      if (!isObject(lateral) || !isObject(lateralNotes)) throw new Error('Invalid Lateral ' + (i + 1) + '.');
      validateBucket(lateral.fields, roots.lateral, false, wellType);
      validateBucket(lateralNotes.fields, roots.lateral, true);
      checkBlockList(lateral.completion_intervals, 'completion_interval');
      checkSameLength(lateralNotes.completion_intervals, lateral.completion_intervals, 'completion_interval');
      lateral.completion_intervals.forEach((comp, j) => {
        const note = lateralNotes.completion_intervals[j];
        if (!isObject(comp) || !isObject(note)) throw new Error('Invalid Completion Interval ' + (j + 1) + '.');
        validateBucket(comp.fields, roots.completion, false, wellType);
        validateBucket(note.fields, roots.completion, true);
        checkBlockList(comp.sand_bodies, 'sand_body');
        checkSameLength(note.sand_bodies, comp.sand_bodies, 'sand_body');
        comp.sand_bodies.forEach((sand, k) => {
          validateBucket(sand, roots.sandBody, false, wellType);
          validateBucket(note.sand_bodies[k], roots.sandBody, true);
        });
      });
    });
    return comments;
  }

  function fillBucket(root, bucket, commentsOnly) {
    if (!commentsOnly) {
      // Populate controlling answers before setting a dependent dropdown.
      // Otherwise its saved option does not exist yet and the browser drops it.
      root.querySelectorAll('select[data-options-by]').forEach((control) => {
        const [triggerName] = Object.keys(JSON.parse(control.dataset.optionsBy));
        const trigger = findParamField(root, triggerName);
        const value = findBucketParamValue(bucket, triggerName);
        if (trigger && value != null) trigger.value = value;
      });
      refreshConditionalOptions(root);
    }
    for (const [category, subcategories] of Object.entries(bucket)) {
      for (const [subcategory, parameters] of Object.entries(subcategories)) {
        for (const [parameter, value] of Object.entries(parameters)) {
          const row = findFieldRow(root, category, subcategory, parameter);
          if (commentsOnly) {
            row.querySelector('.field-comment').value = value;
          } else {
            const unitElement = row.querySelector('.field-unit');
            if (unitElement.tagName === 'SELECT' && isObject(value)) {
              unitElement.value = value.unit;
              unitElement.dataset.currentUnit = value.unit;
              const choice = unitChoice(unitElement, value.unit);
              if (choice.system === 'Field' || choice.system === 'both') {
                unitElement.dataset.lastFieldUnit = value.unit;
              }
              updateUnitLimits(row, choice, unitChoices(unitElement));
            }
            const bare = isObject(value) ? value.value : value;
            if (bare === null) continue;
            const control = row.querySelector('[data-kind]');
            if (control.dataset.kind === 'multi_number') {
              control.querySelectorAll('input').forEach((input, i) => { setNumericValue(input, bare[i]); });
            } else if (control.dataset.kind === 'number') {
              setNumericValue(control, bare);
            } else if (control.dataset.kind === 'masked') {
              setMasked(control, bare);
            } else {
              control.value = bare;
            }
          }
        }
      }
    }
  }

  function restoreData(record) {
    const comments = validateImport(record); // Check before replacing anything the user has typed.
    lateralRepeater.setCount(record.laterals.length);
    sandForm.querySelectorAll('[data-param]').forEach(clearControl);
    sandForm.querySelectorAll('.field-comment').forEach((input) => { input.value = ''; });
    fillBucket(wellSection, record.well, false);
    fillBucket(wellSection, comments.well, true);
    evaluateVisibility(wellSection);
    syncLateralMode();
    lateralBlocks().forEach((lateral, i) => {
      const data = record.laterals[i], notes = comments.laterals[i];
      lateral.completionRepeater.setCount(data.completion_intervals.length);
      fillBucket(ownFields(lateral), data.fields, false);
      fillBucket(ownFields(lateral), notes.fields, true);
      evaluateVisibility(ownFields(lateral));
      completionBlocks(lateral).forEach((comp, j) => {
        const compData = data.completion_intervals[j], compNotes = notes.completion_intervals[j];
        comp.sandBodyRepeater.setCount(compData.sand_bodies.length);
        fillBucket(ownFields(comp), compData.fields, false);
        fillBucket(ownFields(comp), compNotes.fields, true);
        evaluateVisibility(ownFields(comp));
        sandBodyBlocks(comp).forEach((sb, k) => {
          fillBucket(sb, compData.sand_bodies[k], false);
          fillBucket(sb, compNotes.sand_bodies[k], true);
          evaluateVisibility(sb);
        });
      });
    });
    document.getElementById('basis-change-status').textContent = '';
    syncBasisUnits(sandForm); // Validated above, so this only refreshes the offered units.
    refreshCounterValidity();
    syncMaskValidity();
    // A mixed imported record has no saved bulk choice. New repeaters start
    // in Field units deterministically, while existing per-field units stay put.
    lastBulkSystem = unitSystemSelect.value === 'Custom' ? 'Field' : unitSystemSelect.value;
  }

  // Exports are named from the well's anonymized ID, so a reviewer collecting
  // submissions can tell records apart in a download folder without opening
  // them. A draft saved before the ID is complete is named "Unnamed".
  //
  // Repeat exports are deliberately NOT numbered here. A page cannot see the
  // download folder, so an in-page counter would count exports in this session
  // rather than actual filename collisions -- it would stamp "(2)" on the first
  // export after a reload, and miss a real clash with a file saved yesterday.
  // Browsers already uniquify a colliding download themselves, which is both
  // correct and what users expect from every other download they make.
  function exportBaseName() {
    const control = findParamField(wellSection, EXPORT_NAME_PARAM);
    return control && maskComplete(control) ? readMasked(control) : 'Unnamed';
  }

  function download(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  function reportExactValidity() {
    // Native validation must see the exact saved number. A rounded display
    // can otherwise hide an out-of-range value or reject a valid value near
    // a converted fractional bound (for example 0°F in Celsius).
    refreshCounterValidity();
    syncMaskValidity();
    const inputs = Array.from(sandForm.querySelectorAll('input[type="number"]'));
    inputs.forEach((input) => { input.value = exactNumber(input); });
    const valid = sandForm.reportValidity();
    inputs.forEach((input) => { setNumericValue(input, exactNumber(input)); });
    return valid;
  }
  function saveFile(format, draft) {
    if (!draft) {
      if (!reportExactValidity()) return;
    }
    const record = collectData();
    // The filename helps people distinguish files in a folder; this marker
    // survives a rename and lets the JSON/CSV importers identify the status.
    record.record_status = draft ? 'draft' : 'complete';
    const suffix = draft ? '_draft' : '_complete';
    if (format === 'json') {
      download(exportBaseName() + suffix + '.json', JSON.stringify(record, null, 2), 'application/json');
    } else {
      download(exportBaseName() + suffix + '.csv', toCsv(collectCsvRows(record)), 'text/csv');
    }
  }

  // Only three actions are shown in the footer. JSON and CSV are choices
  // within the draft and completed-export menus, so users first choose the
  // operation and then its file format. Both choices call the same serializer.
  document.querySelectorAll('.file-action-menu button[data-format]').forEach((button) => {
    button.addEventListener('click', () => {
      const menu = button.closest('.file-action-menu');
      saveFile(button.dataset.format, menu.dataset.mode === 'draft');
      menu.open = false;
    });
  });

  const importInput = document.getElementById('import-file');
  const importStatus = document.getElementById('import-status');
  document.getElementById('import-btn').addEventListener('click', () => importInput.click());
  importInput.addEventListener('change', async () => {
    const file = importInput.files[0];
    if (!file) return;
    try {
      const content = await file.text();
      const record = file.name.toLowerCase().endsWith('.csv') ? csvToData(content) : JSON.parse(content);
      validateImport(record);
      if (!window.confirm('Importing will replace the current form entries. Continue?')) return;
      restoreData(record);
      importStatus.textContent = 'Loaded ' + file.name +
        (record.record_status ? ' (' + record.record_status + ')' : '') + '.';
    } catch (error) {
      importStatus.textContent = 'Could not load ' + file.name + ': ' + error.message;
      window.alert(importStatus.textContent);
    } finally {
      importInput.value = '';
    }
  });
})();
"""


# Shows a field's "?" tooltip in one element attached to <body>, so no
# section can clip it or paint over it. It sits above the "?" when there is
# room and below it near the top of the window, and stays inside the window
# horizontally. Hover and keyboard focus both show it and Escape hides it.
# Scrolling moves it with its "?" (focusing a field scrolls the page, so
# hiding on scroll would break keyboard use) and hides it once the "?" leaves
# the window. Independent of the form script, so it works on a locked form too.
TOOLTIP_JS = r"""
(function () {
  const tip = document.createElement('div');
  tip.id = 'tooltip';
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  document.body.appendChild(tip);
  let owner = null;
  function show(icon) {
    owner = icon;
    tip.textContent = icon.dataset.tip;
    tip.hidden = false;
    icon.setAttribute('aria-describedby', 'tooltip');
    const gap = 8, margin = 8;
    const box = icon.getBoundingClientRect();
    const width = tip.offsetWidth, height = tip.offsetHeight;
    const above = box.top - gap - height >= margin;
    const left = Math.max(margin, Math.min(box.left - 4, window.innerWidth - width - margin));
    tip.dataset.side = above ? 'above' : 'below';
    tip.style.left = left + 'px';
    tip.style.top = (above ? box.top - gap - height : box.bottom + gap) + 'px';
    tip.style.setProperty('--arrow-left', Math.max(4, box.left + box.width / 2 - left - 5) + 'px');
  }
  function hide() {
    if (owner) owner.removeAttribute('aria-describedby');
    owner = null;
    tip.hidden = true;
  }
  document.addEventListener('mouseover', (event) => {
    const icon = event.target.closest && event.target.closest('.tt');
    if (icon && icon !== owner) show(icon);
  });
  document.addEventListener('mouseout', (event) => {
    const icon = event.target.closest && event.target.closest('.tt');
    if (icon && !icon.contains(event.relatedTarget) && document.activeElement !== icon) hide();
  });
  document.addEventListener('focusin', (event) => { if (event.target.matches('.tt')) show(event.target); });
  document.addEventListener('focusout', (event) => { if (event.target === owner) hide(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') hide(); });
  let queued = false;
  window.addEventListener('scroll', () => {
    if (!owner || queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (!owner) return;
      const box = owner.getBoundingClientRect();
      if (!owner.isConnected || box.bottom < 0 || box.top > window.innerHeight) hide();
      else show(owner);
    });
  }, { passive: true });
})();
"""


def render_html(model: dict, expires_on: str = DEFAULT_EXPIRES_ON, tabbed: bool = True) -> str:
    """The official tabbed form, or with tabbed=False the classic long-page
    layout. Both share the markup and form script; tabbed adds the
    presentation layer in tabbed_layout.py."""
    well_html = render_well_section(model)
    lateral_template_html = render_lateral_template(model)
    js = (JS.replace("__SCHEMA_VERSION__", str(CURRENT_SCHEMA_VERSION))
            .replace("__LIMITS__", json.dumps(model["limits"]))
            .replace("__MULTILATERAL__", json.dumps(MULTILATERAL_PARAMETER))
            .replace("__EXPIRES_ON__", json.dumps(expires_on) if expires_on else "null")
            .replace("__EXPORT_NAME_PARAM__", json.dumps(EXPORT_NAME_PARAM))
            .replace("__CHOICE_DISPLAY__", json.dumps(CHOICE_DISPLAY, ensure_ascii=False))
            .replace("__OIL_FVF__", json.dumps(OIL_FVF))
            .replace("__UNIT_BASIS__", json.dumps(BASIS_DRIVERS))
            .replace("__GAS_FVF__", json.dumps(GAS_FVF)))

    if expires_on:
        cutoff = date.fromisoformat(expires_on)
        display_date = f"{cutoff:%B} {cutoff.day}, {cutoff.year}"
        validity_notice = f"<p class=\"validity-notice\">This form accepts submissions through {display_date}.</p>"
    else:
        validity_notice = ""

    title = "Sand Control Failure Record Form (Producer Wells)"
    css, body_attr, outline, ui_js = CSS, "", "", ""
    if tabbed:
        css += TABBED_CSS
        body_attr = ' class="tabbed"'
        outline = ('<nav id="outline" aria-label="Form sections"><h2>Form sections</h2>'
                   '<div id="problems" role="status" aria-live="polite" hidden></div>'
                   '<ul id="outline-list"></ul></nav>')
        ui_js = f"\n<script>{TABBED_JS}</script>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body{body_attr}>
<header class="page-header">
  <h1>Sand Control Failure Record Form &mdash; Producer Wells</h1>
  <p>Import a saved file, save an unfinished draft, or export a completed record. JSON and CSV are available for both saves. Hover the <strong>?</strong> icon next to a field for guidance.</p>
  <div class="unit-toolbar"><label for="unit-system">Units</label>
    <select id="unit-system" aria-label="Units for the form"><option value="Field" selected>Field</option><option value="SI">SI</option><option value="Custom" disabled>Custom</option></select>
    <small>Well type (or a Sand Body's Fluid Type) sets whether sand rates and PI are liquid- or gas-based; changing it clears numbers entered in the other basis. Standard gas volumes use 60°F and 14.73 psia on both sides.</small>
  </div>
  <p id="basis-change-status" role="status" aria-live="polite"></p>
  {validity_notice}
  <p id="expired-banner" class="expired-banner" style="display:none;">
    This form has expired and is no longer accepting submissions. Please contact your Sand Control Failure DB
    program contact for a current version of the form.
  </p>
</header>
<main>
  {outline}<form id="sand-form" onsubmit="return false;">
    {well_html}
    <div id="laterals-container"></div>
    {lateral_template_html}
  </form>
</main>
<div class="export-bar">
  <input type="file" id="import-file" accept=".json,.csv,application/json,text/csv" hidden>
  <button type="button" id="import-btn">Import file</button>
  <details class="file-action-menu" data-mode="draft">
    <summary>Save draft &#9662;</summary>
    <div class="file-action-options">
      <button type="button" data-format="json">Save JSON draft</button>
      <button type="button" data-format="csv">Save CSV draft</button>
    </div>
  </details>
  <details class="file-action-menu" data-mode="complete">
    <summary>Export completed record &#9662;</summary>
    <div class="file-action-options">
      <button type="button" data-format="json">Export JSON</button>
      <button type="button" data-format="csv">Export CSV</button>
    </div>
  </details>
  <p id="import-status" role="status" aria-live="polite"></p>
</div>
<script>{js}</script>{ui_js}
<script>{TOOLTIP_JS}</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="Path to the dictionary xlsx file")
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT, help="Path to write the generated HTML form")
    parser.add_argument("--classic-output", default=DEFAULT_CLASSIC_OUTPUT,
                        help="Path to write the classic long-page layout of the same form")
    parser.add_argument("--expires-on", default=DEFAULT_EXPIRES_ON,
                         help="ISO date (YYYY-MM-DD) after which the generated form locks itself "
                              "(client-side check baked in at generation time). Pass \"\" for no expiration.")
    args = parser.parse_args()

    if args.expires_on:
        date.fromisoformat(args.expires_on)  # fail fast on a malformed --expires-on value

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    rows = load_dictionary(input_path)
    if not rows:
        raise SystemExit("No rows found in the dictionary sheet.")
    model = build_model(rows)
    html_out = render_html(model, expires_on=args.expires_on)

    output_path = Path(args.output)
    output_path.write_text(html_out, encoding="utf-8")
    classic_path = Path(args.classic_output)
    classic_path.write_text(render_html(model, expires_on=args.expires_on, tabbed=False), encoding="utf-8")
    well_subcats = sum(len(v) for v in model["well"].values())
    lateral_subcats = sum(len(v) for v in model["lateral"].values())
    completion_subcats = sum(len(v) for v in model["completion"].values())
    sand_body_subcats = sum(len(v) for v in model["sand_body"].values())
    print(f"Wrote {output_path} ({len(expand_conditional_rows(rows))} effective parameters: "
          f"{well_subcats} well-scope, {lateral_subcats} lateral-scope, {completion_subcats} completion-interval-scope, "
          f"{sand_body_subcats} sand-body-scope subcategories) and the classic layout {classic_path}.")


if __name__ == "__main__":
    main()
