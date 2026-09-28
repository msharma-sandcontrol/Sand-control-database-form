# Devlog: `feature/form-save-load`

Branch base: `main` at `e231d84`. Period: 2026-09-24 to 2026-09-28.
Author: Fehmi Ozbayrak, with AI coding agents.
Written for developers joining the branch (Javid in particular) and for
coding agents working in this repo. It explains **what changed, why, and which
alternatives were rejected**, so the design is not rediscovered or undone by
accident.

The branch started as "let users save and reload the form". It grew to cover
four areas, and later work changed decisions made earlier on the branch. When
this log and an older commit message disagree, **this log describes the
current state**.

| Area | Result |
|---|---|
| Form files | JSON and CSV drafts or completed records that restore the complete form state |
| Rule parity | The browser form and the API apply the same show/hide and required rules |
| Units | Per-field Field/SI units, stored explicitly and converted without accumulating error |
| Liquid/gas basis | Well type or Fluid Type decides it; the user cannot set it separately (see section 5) |

Where things live:

- Conversion factors and unit rules: [`docs/unit_conversion_review.md`](../unit_conversion_review.md)
- Unit choices and liquid/gas basis rules (code): `dictionary/units.py`
- Bo/Bg row expansion: `dictionary/conditional_fields.py`
- Visibility rule inversion shared by the form and API: `dictionary/visibility.py`
- API validation: `db/mapping.py`, `backend/app/schemas/ingest.py`

---

## 1. Timeline

| Commit | Date | Summary |
|---|---|---|
| `88bd536` | 09-24 | JSON/CSV files that round-trip the form, field comments; workbook: Well Deviation, Screen Size Selection, Fines label |
| `c7815a2` | 09-24 | Draft vs completed files, file naming, `record_status`; workbook: weighting/bridging agent loadings |
| `4f38175` | 09-24 | Interactive form logic explorer (`docs/form_logic_tree.html`) |
| `c17150c` | 09-24 | Visibility parity between form and API; merged failure/performance section; one severity field; `schema_version` 0 |
| `e571276`, `60978c7` | 09-24 | Logic explorer: Required/Optional/Visible/Hidden filters and counts |
| `985921e` | 09-28 | Fix Sand Body parent numbering; severity shown only when Sand failure = Yes; rename to Screen Size Selection Method |
| `db9c845` | 09-28 | Per-field Field/SI unit conversion; units saved in JSON, CSV, and the database |
| `b245ee7` | 09-28 | Well type controls liquid/gas units; Bo and Bg split at row 145; two-decimal numeric display |
| `75bd1e3` | 09-28 | Exact values across repeated unit switching; API returns decimals as strings |
| *(this change)* | 09-28 | Liquid/gas basis simplified to follow answers only; Sand Body falls back to Well type in the API too |

---

## 2. Form files: save, load, draft, complete

- The footer has **Import file**, **Save draft** (JSON or CSV), and **Export
  completed record** (JSON or CSV).
  - **Draft saves** skip validation.
  - **Completed exports** validate all visible fields.
  - **Import** accepts either format and asks for confirmation before
    replacing the current entries.
- Both formats restore everything: values, per-field comments, the number and
  order of Completion Intervals and Sand Bodies, and each field's selected unit.
- **JSON** keeps the API payload shape, `Category → Subcategory → Parameter`.
  It adds a parallel `comments` tree plus the `record_status` and
  `schema_version` fields.
- **CSV** is long format with these columns: Category, Subcategory, Parameter,
  Completion Interval, Sand Body, Value, Unit, Comment, and Row Type. Row Type
  separates field rows from metadata, interval, and sand-body rows.
  Multi-number values are stored as a JSON array in the Value cell, so empty
  positions survive a round trip.
- Filenames are built from the anonymized well name and ID, ending in `_draft`
  or `_complete`. A missing name becomes `Unnamed`.
  - The status is also stored inside the file, so renaming a file cannot turn
    a draft into a completed record.
  - `POST /records` rejects a file explicitly marked as a draft.
- The static form never calls the backend. Connecting exports to the API is
  still a separate, future step.

## 3. Workbook (`MASTER.xlsx`) edits on this branch

| Row(s) now | Change | Migration |
|---|---|---|
| 59 | `Completion Interval Length` replaced by **Well Deviation**, a different measurement, so the column is new rather than renamed | `b7c2d6e1f9a4` |
| 100 | New **Screen Size Selection** dropdown, later renamed **Screen Size Selection Method** (renamed in place, so stored values survive) | `b7c2d6e1f9a4`, `d6e5a1b2c3f4` |
| — | Fines Content: label change only; column renamed in place | `b7c2d6e1f9a4` |
| 73, 74 | New **Weighting Agent Loading** and **Bridging Agent Loading** (lb/bbl, optional, ≥ 0) | `c26f86a72b05` |
| 16–32 | Failure details and production history merged into one always-visible **Sand Production & Well Performance** section. Sand failure = Yes adds only the extra failure questions. | `e41b59c2a7d3` |
| 17 | Separate oil and gas severity fields replaced by one required **Severity of sand production**. It appears only when Sand failure = Yes, and Well type selects the oil or gas thresholds. | `e41b59c2a7d3` |
| 145 | Split into **Oil FVF (Bo)** and **Gas FVF (Bg)**, chosen by the Sand Body's Fluid Type (see section 4) | `b23c45d67e89` |

Migration chain on this branch, oldest first:
`a686239533ca` (main) → `b7c2d6e1f9a4` → `c26f86a72b05` → `e41b59c2a7d3` →
`d6e5a1b2c3f4` → `a12b34c56d78` (unit columns) → `b23c45d67e89` (Bo/Bg).
The current change adds no migration.

## 4. Rule parity between the form and the API (`c17150c`)

**Problem.** The API knew which fields were required, but not the workbook's
show/hide rules. A record the browser considered valid could be rejected for
a field the browser had hidden, for example Water depth on an Onshore well.

**Fix.**

- `dictionary/visibility.py` inverts the workbook's `Affected Subcategory` and
  `Affected Parameter` rules.
- Codegen writes the result into each entry of `field_registry.json`.
- `db/mapping.py` evaluates those rules the same way the form does:
  - A required field is enforced only when it is visible.
  - An answer to a hidden question is rejected.
  - A dropdown whose options depend on another answer (severity by Well type)
    is validated against that answer.
- `tests/api/test_visibility_validation.py` checks this without Postgres, so a
  skipped database suite cannot hide drift.

**Schema version.** JSON and CSV exports carry `schema_version: 0`. Import and
the API require exactly 0, and the value is stored in `well.schema_version`.
Version 0 is a development version that may keep changing until the first
company data arrives. At that point it will be frozen and compatibility paths
added. No legacy parsers exist.

**Logic explorer** (`docs/form_logic_tree.html`, generated). It is a read-only
tree built from the same workbook model. You pick answers and see which rows
are shown or hidden and why. It includes filters and a count of required
questions under the chosen answers. CI's drift check covers it.

## 5. Units

### 5.1 What the form does

- Every field with a unit starts in its Field unit.
- Each convertible field has its own unit selector.
- The top **Field / SI** selector converts every field at once. It shows
  **Custom** when fields are mixed; that state is derived and never saved.
- "SI" means **practical engineering metric** units (m, cm, kPa, °C, Sm³/d,
  mg/L), not strict SI (Pa, K, m³/s). The user chose this.
- Units that are already practical in both systems stay fixed: %, days,
  degrees, L, micron, and md.
- Standard gas volumes use **60 °F / 14.73 psia on both sides**. "Sm³" in this
  form means a cubic metre at that same reference, so converting ft³ to m³ does
  not also change the reference conditions.
- Min/max limits convert along with the unit, including the °F/°C offset. A
  zero minimum always applies.
- Choice labels that contain thresholds (operating environment, severity,
  bean-up) show metric equivalents beside the Field values. The stored option
  values are the workbook's originals, so imports and API checks do not change.
- Numbers display with two decimals when not focused, or in scientific notation
  when very small. Focusing a field shows the full value. Validation,
  conversion, JSON, CSV, and the database always use the full value.

Workbook interpretations adopted, all standard industry usage and recorded in
the review doc:

- **Screen gauge**: 0.001 in of slot opening, so ×25.4 to microns.
- **ppa**: pounds of proppant added per US gallon of clean fluid.
- **Frac gradient in ppg**: equivalent mud weight, converted to kPa/m with
  standard gravity.

Javid's branch pairs these labels with the same target units but defines no
conversions.

### 5.2 How units are stored

- **JSON:** every field that has a unit is `{"value": ..., "unit": ...}`, even
  when blank, so a draft keeps its unit choice.
- **CSV:** the Unit column on each field row.
- **Database:** a `<column>_unit` TEXT column for each parameter with more than
  one unit choice (57 today, including both FVF units). Values are stored in
  the unit the user selected. They are **not** normalized to SI, so analysts
  must use the unit column.
- **API readback:** `{value, unit}`, with Decimal values returned as strings.
  Converting them through a JSON float would change their digits.
- **API validation:** checks the unit against the field's choices, converts
  limits into the selected unit, and applies the liquid/gas rule in 5.4.

### 5.3 Floating-point accuracy (`75bd1e3`)

Computers cannot store most decimals exactly, so a Field → SI → Field round
trip can come back slightly off, for example 100 → 30.48 → 99.99999999999999.
The error (~10⁻¹⁶ relative) means nothing physically, but it makes a saved file
look as if the user typed something else.

**Fix.** Each input remembers the number the user last typed and its unit.
Every conversion starts from that source, never from the previous conversion,
and the result is rounded to 15 significant digits. Switching back to the
source unit restores the typed characters exactly, however many switches
happen in between. Typing a new number resets the source.

**Remaining limitation.** A file saved while in SI holds the converted value
(e.g. `10267.5284233927`), not the Field number the user typed. That is still
far more precise than any field measurement.

### 5.4 Liquid/gas basis: the decision and how it evolved

**The underlying problem.** Seven workbook numeric fields have a unit label
that names two units:

- Rows 25–27, sand rates: `pptb or lb/MMSCF`
- Rows 28, 32, 138, PI: `stb/d/psi or MMSCF/d/psi`
- Row 91, screen opening: `gauge or micron`

Converting between units is easy once the starting unit is known. But
`pptb` measures sand per liquid volume and `lb/MMSCF` measures sand per gas
volume: **two different production streams**. The same number, 10, is about
28.5 mg/L of liquid in pptb, or about 0.16 mg/Sm³ of gas in lb/MMSCF, a
difference of about 178×. There is no conversion between the two streams
without production-ratio data. So the form must know **which basis** a number
was entered in. Screen gauge is simpler: gauge and micron are both lengths, so
the user picks between them freely.

**How the rule evolved:**

1. **`db9c845`.** The user could pick the liquid/gas basis per field. Switching
   a filled field to the other basis asked for confirmation, then cleared it.
2. **`b245ee7`.** Well type also set the basis. The result was two sources of
   truth, which needed confirm dialogs, an export-time "unit conflicts with
   Well type" warning, and clearing logic to reconcile them.
3. **Current (this change).** The basis is **never picked by the user**:
   - Rows 25–28 and 32 follow **Well type**: Oil Producer → liquid; Gas
     Producer and Gas Condensate Producer → gas.
   - Row 138, Sand Body PI, follows **that Sand Body's Fluid Type**: Oil →
     liquid; Condensate, Wet Gas, Dry Gas → gas. While Fluid Type is blank it
     follows Well type; with both blank the form shows liquid.
   - The unit selector offers only Field or SI within the current basis, for
     example `pptb ↔ mg/L liquid` or `lb/MMSCF ↔ mg/Sm³ gas`.
   - Changing Well type or Fluid Type clears numbers entered in the old basis.
     A **popup** (and a status line) says how many were cleared. This is rare:
     both answers normally come before the measurements.
   - Removed: the manual liquid/gas switch, its confirm dialog, and the
     export-time conflict warning. The warning could no longer fire, because
     no path leaves a mismatched unit in the form. Selectors are restricted,
     every answer change re-applies the basis, and import rejects mismatched
     files.
   - **Accepted limitation:** a gas well that reports sand rate per liquid
     volume cannot be entered as such. Use the field's Comment instead.

The mapping from answer to basis is defined once, as `BASIS_DRIVERS` in
`dictionary/units.py`. It reaches the form (the `UNIT_BASIS` constant and the
`data-unit-basis` attribute) and the API (the `unit_basis` rule in
`field_registry.json`) through code generation. A test fails if Well type or
Fluid Type gains a workbook answer that has no basis.

### 5.5 Sand Body with blank Fluid Type: form/API agreement

This case needed a structural change to the API, so it is recorded in detail.

**The problem.** Fluid Type is optional and always shown. Well type is a
**well** answer, but Fluid Type and PI are **Sand Body** answers. The API used
to validate each Sand Body on its own inside `CompletionIntervalIngest`, where
the well is not visible. So when Fluid Type was blank, the API had nothing to
decide the basis with and accepted either one, while the form fell back to
Well type:

| | Well type | Fluid Type | Sand Body PI | Result before |
|---|---|---|---|---|
| Form | Oil Producer | blank | offers only liquid units | gas unit impossible |
| Form import | Oil Producer | blank | `3 MMSCF/d/psi` | rejected |
| API | Oil Producer | blank | `3 MMSCF/d/psi` | **accepted and stored** |

The stored number was not ambiguous, because its unit is saved alongside it.
But the database could contain records that break the stated rule, and the
guarantee that the form and API enforce the same rules was broken. Only
hand-edited or scripted payloads could hit this, but the API is the final
safeguard, so it must enforce the rule.

**Options considered:**

1. **Make Fluid Type required.** A workbook-only change. It was not chosen,
   because Fluid Type is to stay optional.
2. **Give the API the fallback.** Chosen, and described below.
3. **Treat blank Fluid Type as liquid in both.** Rejected: it would silently
   force a gas well's Sand Body PI into liquid units.
4. **Offer both bases when Fluid Type is blank.** Rejected: it brings back the
   manual switch and its confirmation dialog.

**What was implemented:**

- **Registry rule.** `dictionary/units.py::basis_rule()` gives row 138 a
  `fallback` to Well type, and codegen writes it into `field_registry.json`:
  ```json
  "unit_basis": {
    "parameter": "Fluid Type",
    "by_answer": {"Oil": "liquid", "Condensate": "gas", "Wet Gas": "gas", "Dry Gas": "gas"},
    "fallback": {"parameter": "Well type",
                 "by_answer": {"Oil Producer": "liquid", "Gas Producer": "gas",
                               "Gas Condensate Producer": "gas"}}
  }
  ```
- **Parent answers.** `db/mapping.py` gains `flatten_bucket(bucket, scope,
  inherited=None)` and `parent_answers(bucket, scope)`. `inherited` holds the
  parent well's visible answers. `_unit_basis()` checks, in order:
  1. The Sand Body's own answer (Fluid Type).
  2. If that is blank, the inherited fallback (Well type).
  3. If both are blank, no basis is enforced.
- **API schema.** Sand Body validation moved out of `CompletionIntervalIngest`
  into a `completion_intervals` field validator on `RecordIngest`. There,
  `info.data["well"]` is available because `well` is declared first. Errors
  now carry their location, for example:
  ```
  Completion Interval 1, Sand Body 1: Reservoir Characterization /
  Reservoir Rock and Fluid Properties / Initial PI: unit 'MMSCF/d/psi'
  does not match Well type = 'Oil Producer' (Fluid Type is blank)
  ```
- **Saving.** `backend/app/services/record_ingest.py` passes the well's answers
  the same way when it re-flattens Sand Bodies for storage.
- **Form.** Unchanged. It already applied this rule on screen and in import
  validation (`basisForAnswers()` in `form/generate_form.py`).

**Resulting behavior** (tested in `tests/api/test_visibility_validation.py`
and `tests/db/test_unit_mapping.py`):

| Well type | Fluid Type | PI unit | API |
|---|---|---|---|
| Oil Producer | blank | liquid | accept |
| Oil Producer | blank | gas | reject |
| Gas Producer | blank | gas | accept |
| Gas Producer | blank | liquid | reject |
| Oil Producer | Wet Gas | gas | accept (the Sand Body's own answer wins) |
| Gas Producer | Oil | gas | reject |
| blank | blank | any | the record is already rejected because Well type is required, so no basis is enforced |

**Things to know before extending this:**

- This is the API's **first rule that crosses levels**, with a Sand Body
  depending on a well answer. Any new rule of this kind should reuse the same
  path: the `fallback` in the registry plus `inherited` in `flatten_bucket`.
  Don't add special cases.
- If the well bucket itself fails validation, Sand Bodies are checked without
  the fallback. The request fails regardless, and this avoids reporting
  errors that follow only from the broken well.
- The form shows liquid when both answers are blank; the API enforces nothing
  in that case. The two never disagree on a record the API would accept.
- There is no schema or migration change. Stored records and
  `GET /records/{id}` are unaffected.

### 5.6 Oil vs gas formation volume factor (row 145, `b245ee7`)

- Row 145 expands into two parameters, each with its own database column:
  - `Oil Formation Volume Factor (Bo) at downhole conditions`, in `rb/STB` or
    m³ reservoir/m³ stock tank.
  - `Gas Formation Volume Factor (Bg) at downhole conditions`, in
    `res ft³/scf`, `rb/scf`, or m³ reservoir/Sm³ gas.
- Fluid Type Oil shows Bo; Condensate, Wet Gas, and Dry Gas show Bg.
- Changing Fluid Type clears the other alternative, including its comment.
- Import and the API reject a value in the alternative that does not match
  Fluid Type.
- The expansion lives in `dictionary/conditional_fields.py`, so the form, the
  codegen, and the logic explorer share it.

## 6. API contract changes (summary)

- **Payload:** the same nested shape as before, plus:
  - `schema_version` (required, must be 0)
  - `record_status` (optional; `draft` is rejected)
  - `comments` (optional; must mirror the interval and sand-body counts)
  - `{value, unit}` objects for fields that have units
- **Validation:**
  - Required fields are enforced only when visible, and hidden answers are
    rejected.
  - Options depend on Well type where the workbook says so.
  - Units must be among the field's choices and match the liquid/gas basis.
  - Limits apply in the selected unit.
- **Readback:** numbers come back as strings and include their units.
  `schema_version` and `raw_payload` (with comments) are kept.

## 7. Verification status

- Python: 105 passed, 19 skipped. The skipped tests are the Postgres-backed
  ones: submission, fetch, and migrations. No Postgres was available on the
  development machine, so **CI's Postgres job is the first real run** of the
  saving path, including the new `inherited` argument in `record_ingest.py`.
- Ruff and the codegen drift check (regeneration produces no diff) pass.
- Headless Chromium checks covered:
  - basis per Well type and Fluid Type, including the fallback and the popups
  - exact values after repeated Field/SI switching
  - JSON draft round trip with units
  - rejection of a tampered import
  - earlier commits: CSV round trips, severity branches, Bo/Bg switching,
    nested renumbering

## 8. Open questions for review

- **Screen gauge, ppa, and frac-gradient ppg:** standard meanings were
  adopted (section 5.1). Confirm that they match the workbook authors' intent.
- **Fluid Type:** keep it optional (current behavior), or make it required?
  Making it required would remove the need for the fallback, but the fallback
  is harmless to keep.
- **Mixed units in storage:** values are stored in the unit chosen per field,
  not normalized. If analysis needs one unit system, add normalized SI columns
  or a view later; don't change stored values.
- **Earlier items still open in `CLAUDE.md`:** Chemical Sand Consolidation,
  Mud PSD sub-labels, and the PSD having 5 values instead of 6.
