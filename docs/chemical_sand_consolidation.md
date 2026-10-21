# Chemical Sand Consolidation: removed on purpose

**Status:** closed. Chemical Sand Consolidation was removed deliberately during
the dictionary redesign. Recorded 2026-10-21.

## Summary

Chemical sand consolidation means injecting resin or another chemical into the
formation so the sand grains bond in place. It is a sand-control method in its
own right, used instead of screens or gravel packs. The original long-format
Data Dictionary had a whole section for it. The current `MASTER.xlsx` does not.

The subject-matter-expert redesign notes in `Changes to Excel sheet.docx` say:

> Delete Rows 156 to 179 (eliminate chemical consolidation)

The removal was deliberate. The project records mechanical sand control
(open-hole and cased-hole completions, screens, gravel packs, frac packs) and
leaves chemical consolidation out.

## Before and after

| Aspect | Original long-format Data Dictionary | `MASTER.xlsx` today |
|---|---|---|
| Chemical consolidation section | Subcategory `Chemical Sand Consolidation` under `Sand Control`, rows 156-179 (about 24 questions) | None |
| Open-hole sand-control methods | Unknown (original not available) | `OH Sand Control Selected Method`: OHGP, SAS (no consolidation option) |
| Cased-hole sand-control methods | Unknown (original not available) | `CH Sand Control Selected Method`: CHFP, CHGP, Cased and Perforated (no consolidation option) |
| `Proppant Type` options | Natural Sand, Resin-Coated Sand, Ceramic Proppant | Natural Sand, Ceramic Proppant |
| `Sand Control` category | Its own category | Merged into `Completion` (Subcategories `Sand Control Details`, `Liners and Screens`, `Gravel Packing`, and others) |

## Timeline

| Date | Source | Event |
|---|---|---|
| Before 2026-08-09 | Original long-format Data Dictionary (not in this repo) | Chemical Sand Consolidation present at rows 156-179 |
| Before 2026-08-09 | `Changes to Excel sheet.docx` | SME notes say to delete rows 156-179 to eliminate chemical consolidation |
| 2026-08-09 | First committed `MASTER.xlsx` (`8cbd48c`, 138 rows) | Already removed. `Proppant Type` still lists Resin-Coated Sand. |
| 2026-08-16 | `4db84d0` | Last version with Resin-Coated Sand |
| 2026-08-30 | `ed97fe9` "updated the form based on latest group feedback" | Resin-Coated Sand dropped from `Proppant Type` |
| 2026-10-21 | Current `MASTER.xlsx` (149 rows) | No resin or consolidation content anywhere |

## Sources and limits

- The original long-format Data Dictionary is not in git or anywhere on the
  development machine, so the exact 24 questions it held cannot be listed. The
  row range and the reason for removing it come from
  `Changes to Excel sheet.docx`.
- Every committed version of `MASTER.xlsx` (12 commits, 2026-08-09 to
  2026-09-28) was searched for "consolidation", "resin" and "chemical". The only
  matches are the Resin-Coated Sand proppant option (until 2026-08-16) and the
  unrelated `Known sand face production chemistry issues` question.

## If it is ever brought back

To include consolidated wells, the smallest change is to add a consolidation
option to the two `Sand Control Selected Method` dropdowns. Those answers could
then show a new `Chemical Consolidation` Subcategory under `Completion`, at
Completion Interval scope, alongside `Gravel Packing`. The usual workbook
workflow in `CLAUDE.md` applies: codegen, form, logic explorer, migration and
tests.
