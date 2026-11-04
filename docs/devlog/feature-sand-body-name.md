# Devlog: `feature/sand-body-name`

Branch base: `067f76d` (contains everything on `main`). Period: 2026-11-03.
Author: Fehmi Ozbayrak, with AI coding agents.
Written for developers and coding agents working in this repo. It records
**what changed, why, and which alternatives were rejected** in the November
2026 SME round, so the design is not rediscovered or undone by accident.

| Area | Result |
|---|---|
| Form lock | The 2026-11-01 expiration had locked every copy of the form; expiration is now off by default |
| Date import | Non-`YYYY-MM-DD` dates are refused on import instead of silently blanked |
| Wording | Sand Control Failure, Well Specific Information, sand-body pressure and PI labels |
| Multilateral wells | A Lateral level between Well and Completion Interval |
| Counters | One counter + Apply per level is the only way to size it; the API enforces it |
| IDs | Masked Well and Field IDs replace Well name and Field name |
| Units and fields | bar replaces kPa; failure durations became dates; condensate gets Dew Point and CGR |

Where things live:

- Levels, counters, caps: `dictionary/structure.py`
- ID masks: `dictionary/masks.py` (the `mask` / `same_code_as` Data Validation modifiers)
- Form behavior: the `JS` block in `form/generate_form.py`
- API structure checks: `backend/app/schemas/ingest.py` (`_validate_counts`)
- Migrations: `c8d1e2f3a4b5` (wording, start-up date), `d9e0f1a2b3c4` (laterals and the rest)

---

## 1. Expiration lock and date import

**Symptom reported:** dates were lost after saving a draft and importing it.

**Findings.** On the branch the whole form was locked: the baked-in
`DEFAULT_EXPIRES_ON = "2026-11-01"` had passed, so every input was disabled.
A colleague's fix on another remote set the constant to `""` but also
hand-edited the generated HTML (leaving comment residue) and did not
regenerate `form/sand_control_form.html`, which would fail the CI drift check.
The fix here changes only the generator and regenerates.

With the form unlocked, JSON and CSV drafts round-trip dates correctly. The
real loss happens when a CSV is opened and re-saved in Excel: Excel rewrites
`2024-01-10` as `1/10/2024`, and a date input silently discards any value
that is not `YYYY-MM-DD`, so import reported success with the dates blank.

**Decision.** Import now refuses such a file and names the field. **Rejected:**
auto-converting `1/10/2024`. Excel writes month-first or day-first depending on
the user's locale, and a wrong guess would corrupt data silently. The API
already rejected non-ISO dates, so the form now matches it.

## 2. Multilateral wells: the Lateral level

`Is this a Multilateral Well?` (required Yes/No) follows Well type; Yes shows
the required `Number of laterals` (2-100, the main bore counts as Lateral 1).
Every well now has the hierarchy Well -> Lateral -> Completion Interval ->
Sand Body; a well that is not multilateral has exactly one lateral and the
form hides its banner, so it looks as before. TD (MD and TVD) and `Number of
Completion Intervals` moved from the well into each lateral's `Lateral
Details`, because each branch has its own TD.

**Rejected:** tagging each completion interval with a lateral number instead of
a real level. It would avoid a table but cannot hold per-lateral fields such as
TD, and the form would need a second grouping mechanism next to its repeaters.

**Table name.** The table is `well_lateral`, not `lateral`: `LATERAL` is a
reserved word in Postgres and SQLAlchemy does not quote it, so `CREATE TABLE
lateral` fails. The payload and registry key stays `lateral`.

**Migration.** `d9e0f1a2b3c4` moves existing data rather than dropping it:
each well gets Lateral 1 with its old TD and counter, and its intervals are
re-parented. The downgrade folds other laterals' intervals back into the well
after Lateral 1's. Both directions were exercised on real rows, and `alembic
check` reports no difference from the models.

## 3. Counters size their levels

Before: the counters were informational, the Apply button grew *and shrank*
silently (the old docs wrongly said it only grew), and separate add/remove
buttons also changed the blocks. Now each level is controlled from one place:

- The counter's Apply adds or removes blocks at the end. Removing blocks that
  hold data asks first (counters themselves do not count as data); Cancel
  restores the old count. There are no add/remove buttons.
- Interval and sand-body counters start at 1, matching the one block present.
- A typed but unapplied counter is a validity error, so a completed export
  stops on it ("Press Apply to match"). Drafts save it as typed.
- Turning the multilateral answer away from Yes removes Laterals 2+ (with the
  same confirmation); Cancel restores Yes.
- The API checks the same: counters equal block counts, one lateral unless
  multilateral, 1 to cap blocks per level, at least one sand body per interval.

Caps come from each counter's workbook `max` (100 / 10 / 10), read by both the
form and the API, so the old `--max-completion-intervals` / `--max-sand-bodies`
generator flags were removed. **Why 100 laterals:** fishbone wells can have
dozens of branches; the cap only guards against a typo creating hundreds of
blocks, now that the count builds them.

## 4. Visibility bug fixed: rules read their own block

Found while adding the third level. Each block re-evaluates its whole subtree
on change, but triggers were looked up from the listener's root, which finds
the *first* nested block's answer. Choosing Wet Gas in Sand Body 2 was undone
by its parent re-reading Sand Body 1's blank Fluid Type, so Bo stayed visible
and Bg hidden -- and the API (which evaluates each body correctly) would then
reject the record. `findParamField` now only returns a control from the
target's own block. A third level would have spread the same bug to
Completion Interval 2+.

## 5. Masked IDs

`{"Text": {"mask": "AAA-I-#####"}}` -- `A` capital letter, `#` digit, other
characters fixed. The form draws `[XOM]-I-[00001]`: letters capitalized as
typed, focus moves on when a box fills, Backspace in an empty box goes back,
and pasting a whole ID fills every box. The saved value is the joined string,
so a draft can keep a half-typed ID. The API uses the regex derived from the
same mask. `same_code_as` makes the optional Field ID (`AAA-F-###`) share the
Well ID's company code. Files are named after the complete Well ID.

**Detail.** Mask regexes escape only regex syntax characters: `re.escape`
turns `-` into `\-`, which browsers reject in an HTML `pattern` (compiled in
Unicode mode).

## 6. Other workbook edits

- Failure "Time to ..." durations (days) became `Date of first choke back`,
  `Date of well shut-in due to sand`, `Date of complete well failure`. They
  stay optional: the old cells put `required` outside the type
  (`{"required": True, "Decimal": ...}`), which never parsed, so they were
  effectively optional already, and a failed well may never have been shut in.
- Fluid Type: Condensate shows Dew Point Pressure (Pd) and CGR and hides Bo,
  Bubble Point, and Rs; Wet Gas and Dry Gas hide the oil properties too.
- SI pressure is bar (PI per bar, frac gradient bar/m, compressibility
  10⁻⁶/bar). Units are stored as text beside values, so no schema change.
- Drill Bit Size has a fixed `in` unit; OHFP was added as an open-hole method
  but reveals no extra fields yet (open question for the SMEs).
- Rows are renumbered after every edit; see the current numbers in the form.

## 7. Verification

- pytest: 144 passed against a real Postgres (pgserver), including migration
  round trips and new tests in `tests/api/test_structure_and_ids.py`.
- `alembic check`: no difference between migrations and models.
- Browser (headless Chromium): 36 checks covering laterals, nested Apply,
  removal prompts, the multilateral toggle, per-block visibility, masks, and
  JSON/CSV round trips of a multilateral record.

## 8. Open questions

- Which fields should OHFP reveal?
- Should the failure dates be checked for order (first choke back <= shut-in
  <= complete failure)?
- Schema version 0 is still mutable. When it is frozen as version 1, add a test
  that fails if the registry changes without a version bump.
