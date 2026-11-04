# Chemical Sand Consolidation: removed on purpose

**Status:** closed. Chemical Sand Consolidation was removed deliberately during
the dictionary redesign, before this repository's first commit. Recorded
2026-10-21; corrected 2026-11-03 after the original dictionary was found.

## Summary

Chemical sand consolidation means injecting resin or another chemical into the
formation so the sand grains bond in place. It is a sand-control method in its
own right, used instead of screens or gravel packs. The original long-format
Data Dictionary had a whole section for it. `MASTER.xlsx` has never had it.

The subject-matter-expert redesign notes in `Changes to Excel sheet.docx` end
with:

> Delete Rows 156 to 179 (eliminate chemical consolidation)

The removal was deliberate. The project records mechanical sand control
(open-hole and cased-hole completions, screens, gravel packs, frac packs) and
leaves chemical consolidation out.

## What was removed

The original's `Main Sheet` holds the section at rows 155-178: a heading
(`Sand Control | Chemical Sand Consolidation`, row 155) and 23 questions (rows
156-178), followed by a blank row 179:

Sand Consolidation Type; Chemical System Type; Preflush Pumped; Preflush Fluid
Type; Preflush Volume; Consolidation Chemical Volume; Chemical Concentration;
Overflush Pumped; Overflush Fluid Type; Overflush Volume; Max Pump Rate; Max
Pump Pressure; Treatment Placement Method; Diversion Used; Diversion Type;
Shut-In / Cure Time; Cure Temperature; Treatment Successfully Placed;
Post-Treatment Cleanup Performed; Post-Treatment Productivity Change;
Post-Treatment Sand Production Change; Retreatment Required; Placement Issues.

The SME notes' row numbers are not exact (their "row 153, pack efficiency" is
row 152 in this file), so "156 to 179" may mean 155-178. Either reading covers
only this section and the blank row after it: no unrelated question was
deleted with it. The gravel-pack questions just above (rows 141-153, including
the separate gravel-pack `Placement Issues` at row 153) were kept.

The original's single `Selected Method` dropdown (row 129) also offered
`Chemical Sand Consolidation` as a method. That option went with the section.

## Before and after

| Aspect | Original long-format Data Dictionary | `MASTER.xlsx` (2026-11-03) |
|---|---|---|
| Chemical consolidation section | Heading at row 155 and 23 questions at rows 156-178 of `Main Sheet` | None |
| Sand-control methods | One `Selected Method` list: OHGP, SAS, CHFP, CHGP, Cased and Perforated, Chemical Sand Consolidation | Split by completion type. `OH Sand Control Selected Method`: OHGP, OHFP, SAS. `CH Sand Control Selected Method`: CHFP, CHGP, Cased and Perforated. No consolidation option. |
| `Sand Control` category | Its own category | Merged into `Completion` (Subcategories `Sand Control Details`, `Liners and Screens`, `Gravel Packing`, and others) |

**Not part of this decision:** `Resin-Coated Sand` was a `Proppant Type` option
for gravel packs, not a consolidation treatment. It survived the redesign and
was dropped separately on 2026-08-30 (`ed97fe9`, "updated the form based on
latest group feedback"), leaving Natural Sand and Ceramic Proppant.

## Timeline

| Date | Source | Event |
|---|---|---|
| 2026-06-05 | Original long-format Data Dictionary (OneDrive, see below) | Chemical Sand Consolidation present at `Main Sheet` rows 155-178 |
| Before 2026-08-09 | `Changes to Excel sheet.docx` | SME notes say to delete rows 156 to 179 to eliminate chemical consolidation |
| 2026-08-04 | Early MasterView draft (OneDrive, see below) | Already removed; `Proppant Type` still lists Resin-Coated Sand |
| 2026-08-09 | First committed `MASTER.xlsx` (`8cbd48c`, 138 rows) | Still removed |
| 2026-08-30 | `ed97fe9` | Resin-Coated Sand dropped from `Proppant Type` (a separate change) |
| 2026-11-03 | Current `MASTER.xlsx` | No consolidation content anywhere |

## Sources

- Original long-format Data Dictionary, not in git:
  `OneDrive - The University of Texas at Austin/Desktop/work/sand_control/files/Sand_Control_Failure_Record_Form_For_Producer_Wells.xlsx`
  (sheets `Data Dictionary` and `Main Sheet`, dated 2026-06-05). A
  byte-identical copy sits beside it as `..._Fehmis_Copy.xlsx`.
- Early MasterView draft, not in git:
  `OneDrive - The University of Texas at Austin/Desktop/Sand_Control_Failure_Record_Form_For_Producer_Wells_DICTIONARY2.xlsx`
  (dated 2026-08-04, 122 rows).
- `Changes to Excel sheet.docx`, in this repository since its first commit.
- Every committed version of `MASTER.xlsx` was searched for "consolidation",
  "resin" and "chemical". The only matches are the Resin-Coated Sand proppant
  option (until 2026-08-16) and the unrelated tooltip of `Known sand face
  production chemistry issues`.

The first version of this note (2026-10-21) said the original could not be
found. It had been searched for inside WSL only; the OneDrive copies above were
found on 2026-11-03 and confirm the conclusion.

## If it is ever brought back

To include consolidated wells, the smallest change is to add a consolidation
option to the two `Sand Control Selected Method` dropdowns. Those answers could
then show a new `Chemical Consolidation` Subcategory under `Completion`, at
Completion Interval scope, alongside `Gravel Packing`. The 23 original questions
listed above are the starting point. The usual workbook workflow in `CLAUDE.md`
applies: codegen, form, logic explorer, migration and tests.
