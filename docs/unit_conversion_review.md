# Unit conversion review

This is the conversion inventory for the 71 unit-bearing workbook rows plus
the conditional Gas Bg alternative to row 145 (72 effective fields) in
`MASTER.xlsx` (branch `feature/form-save-load`). The form implements these
conversions, and this file records the factors and assumptions for review.
Standard gas volumes on both the Field and SI sides use **60°F (15.5556°C) and 14.73 psia (101.56 kPa absolute)**. The SI
label `Sm³` in this form means a cubic metre at that same reference, so a
geometric ft³ ↔ m³ conversion does not also change reference conditions.
This is the [EIA natural-gas reporting basis](https://www.eia.gov/naturalgas/monthly/pdf/front_matter.pdf),
and it is not 25°C/1 atm. Standard liquid barrels refer to stock-tank liquid
at 60°F; the volume factors below assume the same liquid reference conditions
on both sides. "SI" below means practical engineering metric
units: unchanged units such as %, days, degrees, L, micron, and md stay as they
are. A multiplier means `SI value = Field value × multiplier`; temperature
uses the formula shown. Automatic conversions retain 15 significant digits;
repeated switches can still accumulate a small floating-point difference.

| Workbook row(s) | Field unit | SI unit | Field → SI rule | Review note |
| --- | --- | --- | --- | --- |
| 8, 10, 11, 64, 65, 78, 79 | ft | m | × 0.3048 | Exact international foot. |
| 18–20 | days | days | × 1 | Keep practical time unit. |
| 25–27 | pptb (liquid basis) | mg/L liquid | × 2.8530101742 | One pound per 1,000 petroleum barrels. |
| 25–27 | lb/MMSCF (gas basis) | mg/Sm³ gas | × 16.018463374 | Same 60°F/14.73 psia gas reference on both sides. |
| 28, 32, 138 | stb/d/psi (liquid PI) | Sm³ liquid/d/kPa | × 0.023059157584 | Same stock-tank liquid reference on both sides. |
| 28, 32, 138 | MMSCF/d/psi (gas PI) | Sm³ gas/d/kPa | × 4107.0113694 | Same 60°F/14.73 psia gas reference on both sides. |
| 41, 42, 45–47, 49 | stb/d | Sm³/d | × 0.158987294928 | Same stock-tank liquid reference on both sides. |
| 43, 44, 48 | MMSCF/d | Sm³/d | × 28316.846592 | Same 60°F/14.73 psia gas reference on both sides. |
| 50, 102, 115, 118, 124, 137, 139 | % | % | × 1 | Keep percentage scale. |
| 52, 53, 85, 114, 125–127, 129, 130, 147 | psi | kPa | × 6.8947572932 | Pressure, pressure difference, or strength. |
| 59 | degrees | degrees | × 1 | Keep angle convention (0° vertical, 90° horizontal). |
| 62, 63, 77, 80, 93 | inch | cm | × 2.54 | Exact. |
| 70, 110 | ppg (fluid density) | g/cm³ | × 0.11982642732 | One pound mass per US gallon. |
| 73, 74 | lb/bbl | kg/m³ | × 2.8530101742 | One pound mass per petroleum barrel. |
| 76 | L | L | × 1 | Keep practical volume unit. |
| 81 | shots/ft | shots/m | × 3.2808398950 | Count per length. |
| 91 | screen gauge | micron | × 25.4 | One screen-gauge point is treated as 0.001 inch of opening width. |
| 91, 92, 136 | micron | micron | × 1 | The six row-136 PSD numbers share this unit. |
| 106, 111 | lbs/ft | kg/m | × 1.4881639436 | One pound mass per foot. |
| 112 | ppa | kg/m³ of clean fluid | × 119.82642732 | One pound of proppant added per US gallon of clean fracturing fluid. |
| 113 | bpm | L/s | × 2.6497882488 | Petroleum barrels per minute. |
| 128 | degF | °C | (°F − 32) × 5/9 | Temperature has an offset, not a single multiplier. |
| 132, 133 | microsips | 1/Pa | × 1.4503773773 × 10⁻¹⁰ | One microsip = 10⁻⁶/psi; matches advisor branch's target label. |
| 140 | md | md | × 1 | Keep practical permeability unit. |
| 141, 142 | md-ft | md-m | × 0.3048 | Only the length changes. |
| 145 (Oil Bo) | rb/STB | m³ reservoir/m³ stock tank | × 1 | Same volume unit in numerator and denominator; [BOEM defines Bo as reservoir barrels per stock-tank barrel](https://www.boem.gov/Instructions-BOEM-0127/). |
| 145 (Gas Bg) | reservoir ft³/scf | m³ reservoir/Sm³ gas | × 1 | Both volumes change from ft³ to m³; gas standard remains 60°F/14.73 psia. |
| 145 (Gas Bg) | rb/scf | m³ reservoir/Sm³ gas | × 5.6145833333 | Alternative gas Field unit: one reservoir barrel is 5.6145833333 ft³. |
| 146 | cP | Pa·s | × 0.001 | Dynamic viscosity. |
| 148 | scf/stb | Sm³/Sm³ | × 0.17810760668 | Gas basis: 60°F/14.73 psia; liquid basis: stock tank at 60°F. |
| 149 | ppg (equivalent mud weight for frac gradient) | kPa/m | × 1.1750958334 | Treats the row as equivalent mud weight and uses standard gravity. |

## Selection and save rules

- Every unit-bearing field starts in a Field unit. Bo uses rb/STB; Bg offers
  reservoir ft³/scf and rb/scf as Field choices, plus m³/Sm³ gas as its metric
  choice. Both FVF alternatives are numbered 145. Sand-body Fluid Type shows
  and saves only Bo for Oil, or Bg for Condensate, Wet Gas, and Dry Gas.
- Combined liquid/gas fields initially use the liquid Field choice until
  Well type is selected. Selecting or changing Well type sets their basis to
  liquid for Oil Producer or gas for Gas/Gas Condensate Producer. Values in
  the old basis clear because there is no valid conversion without production
  ratio data. Newly added Sand Bodies follow the selected Well type.
- Manual Field ↔ SI changes convert within the selected basis. A manual
  liquid ↔ gas change with an entered value asks whether to clear it; Cancel
  retains the original unit and value. The top Field/SI selector converts all
  fields within their current basis and derives Custom from mixed choices.
- Completed exports warn if a populated field still has a unit incompatible
  with Well type. Draft saves do not warn. JSON and CSV save selected units,
  including blank fields; the inactive Bo/Bg alternative is omitted. The
  top Field/SI/Custom selector is derived and is never saved.
- Numeric controls show two decimal places when unfocused, or scientific
  notation for tiny nonzero values. Focusing reveals the full value, which
  is used for validation, conversion, JSON, CSV, and database storage.
- Hard-criterion choices (operating environment, severity, bean-up) show
  metric thresholds beside the original Field thresholds. Their stored option
  values stay as defined in the workbook.

## Sources for constants and terms

- [NIST Guide to the SI, Appendix B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8): foot, inch, pound, petroleum barrel, cubic foot, psi, centipoise, temperature.
- [SLB oil FVF glossary](https://glossary.slb.com/terms/o/oil_formation_volume_factor) and [gas FVF glossary](https://glossary.slb.com/Terms/g/gas_formation_volume_factor.aspx): reservoir-volume-to-standard-volume definitions.
- [SLB Oilfield Review](https://www.slb.com/-/media/files/oilfield-review/1-unlocking--english.ashx): ppa as a pound of proppant added per gallon of fracturing fluid.
- [SLB mud density glossary](https://glossary.slb.com/terms/m/mud_density) and [equivalent circulating density glossary](https://glossary.slb.com/terms/e/equivalent_circulating_density): ppg density and its relation to pressure gradient.
- [Weatherford screen sizing table](https://www.weatherford.com/documents/catalog/gravel-pack-systems/): screen-gauge numbers alongside opening sizes, consistent with thousandths of an inch.
