# Unit conversion review

This is the conversion inventory for the 71 unit-bearing workbook rows plus
the conditional Gas Bg alternative to row 146 (72 effective fields) in
`MASTER.xlsx`. The form implements these conversions, and this file records
the factors and assumptions for review.
Standard gas volumes on both the Field and SI sides use **60°F (15.5556°C) and 14.73 psia (1.0156 bar absolute)**. The SI
label `Sm³` in this form means a cubic metre at that same reference, so a
geometric ft³ ↔ m³ conversion does not also change reference conditions.
This is the [EIA natural-gas reporting basis](https://www.eia.gov/naturalgas/monthly/pdf/front_matter.pdf),
and it is not 25°C/1 atm. Standard liquid barrels refer to stock-tank liquid
at 60°F; the volume factors below assume the same liquid reference conditions
on both sides. "SI" below means practical engineering metric
units: pressure is in bar, and unchanged units such as %, degrees, L, micron,
and md stay as they are. A multiplier means `SI value = Field value × multiplier`; temperature
uses the formula shown. Each conversion starts from the number the user
last typed, not from the previous conversion, and keeps 15 significant
digits. Switching back to the typed unit restores the typed digits exactly,
however many times the units are switched.

| Workbook row(s) | Field unit | SI unit | Field → SI rule | Review note |
| --- | --- | --- | --- | --- |
| 9, 57, 58, 65, 66, 79, 80 | ft | m | × 0.3048 | Exact international foot. Rows 57–58 are each lateral's TD. |
| 25–27 | pptb (liquid basis) | mg/L liquid | × 2.8530101742 | One pound per 1,000 petroleum barrels. |
| 25–27 | lb/MMSCF (gas basis) | mg/Sm³ gas | × 16.018463374 | Same 60°F/14.73 psia gas reference on both sides. |
| 28, 32, 139 | stb/d/psi (liquid PI) | Sm³ liquid/d/bar | × 2.3059157584 | Same stock-tank liquid reference on both sides. |
| 28, 32, 139 | MMSCF/d/psi (gas PI) | Sm³ gas/d/bar | × 410701.13694 | Same 60°F/14.73 psia gas reference on both sides. |
| 40, 41, 44–46, 48 | stb/d | Sm³/d | × 0.158987294928 | Same stock-tank liquid reference on both sides. |
| 42, 43, 47 | MMSCF/d | Sm³/d | × 28316.846592 | Same 60°F/14.73 psia gas reference on both sides. |
| 49, 103, 116, 119, 125, 138, 140 | % | % | × 1 | Keep percentage scale. |
| 51, 52, 86, 115, 126–128, 130, 131, 148, 150 | psi | bar | × 0.068947572932 | Pressure, pressure difference, or strength. 1 bar = 100 kPa exactly. |
| 60 | degrees | degrees | × 1 | Keep angle convention (0° vertical, 90° horizontal). |
| 63, 64, 78, 81, 94 | inch | cm | × 2.54 | Exact. |
| 69 | in | in | × 1 | Drill Bit Size: bit sizes are quoted in inches in both systems. |
| 71, 111 | ppg (fluid density) | g/cm³ | × 0.11982642732 | One pound mass per US gallon. |
| 74, 75 | lb/bbl | kg/m³ | × 2.8530101742 | One pound mass per petroleum barrel. |
| 77 | L | L | × 1 | Keep practical volume unit. |
| 82 | shots/ft | shots/m | × 3.2808398950 | Count per length. |
| 92 | screen gauge | micron | × 25.4 | One screen-gauge point is treated as 0.001 inch of opening width. |
| 92, 93, 137 | micron | micron | × 1 | The six row-137 PSD numbers share this unit. |
| 107, 112 | lbs/ft | kg/m | × 1.4881639436 | One pound mass per foot. |
| 113 | ppa | kg/m³ of clean fluid | × 119.82642732 | One pound of proppant added per US gallon of clean fracturing fluid. |
| 114 | bpm | L/s | × 2.6497882488 | Petroleum barrels per minute. |
| 129 | degF | °C | (°F − 32) × 5/9 | Temperature has an offset, not a single multiplier. |
| 133, 134 | microsips | 10⁻⁶/bar | × 14.503773773 | One microsip = 10⁻⁶/psi, and 1/psi = 14.5038/bar. |
| 141 | md | md | × 1 | Keep practical permeability unit. |
| 142, 143 | md-ft | md-m | × 0.3048 | Only the length changes. |
| 146 (Oil Bo) | rb/STB | m³ reservoir/m³ stock tank | × 1 | Same volume unit in numerator and denominator; [BOEM defines Bo as reservoir barrels per stock-tank barrel](https://www.boem.gov/Instructions-BOEM-0127/). |
| 146 (Gas Bg) | reservoir ft³/scf | m³ reservoir/Sm³ gas | × 1 | Both volumes change from ft³ to m³; gas standard remains 60°F/14.73 psia. |
| 146 (Gas Bg) | rb/scf | m³ reservoir/Sm³ gas | × 5.6145833333 | Alternative gas Field unit: one reservoir barrel is 5.6145833333 ft³. |
| 147 | cP | Pa·s | × 0.001 | Dynamic viscosity. |
| 149 | scf/stb | Sm³/Sm³ | × 0.17810760668 | Gas basis: 60°F/14.73 psia; liquid basis: stock tank at 60°F. |
| 151 | stb/MMscf | Sm³/10⁶ Sm³ | × 5.6145833333 | Condensate-to-gas ratio: one barrel is 5.6146 ft³; both volumes at standard conditions. |
| 152 | ppg (equivalent mud weight for frac gradient) | bar/m | × 0.011750958334 | Treats the row as equivalent mud weight and uses standard gravity. |

## Selection and save rules

- Every unit-bearing field starts in a Field unit. Bo uses rb/STB; Bg offers
  reservoir ft³/scf and rb/scf as Field choices, plus m³/Sm³ gas as its metric
  choice. Both FVF alternatives are numbered 146. Sand-body Fluid Type shows
  and saves only Bo for Oil, or Bg for Condensate, Wet Gas, and Dry Gas.
- Sand rates (rows 25–27) and PI (rows 28, 32, 139) have liquid and gas
  units. Well type chooses the basis for rows 25–28 and 32: liquid for Oil
  Producer, gas for Gas and Gas Condensate Producer. Row 139 follows its own
  Sand Body's Fluid Type: liquid for Oil, gas for Condensate, Wet Gas, and
  Dry Gas. It uses Well type while Fluid Type is blank, and liquid when both
  are blank. Each selector offers only Field or SI within the chosen basis.
- Changing Well type or Fluid Type clears numbers entered in the old basis,
  because there is no valid conversion without production ratio data. A
  popup states how many were cleared. The top Field/SI selector converts all
  fields within their current basis and derives Custom from mixed choices.
- JSON and CSV save selected units, including blank fields; the inactive
  Bo/Bg alternative is omitted. Import and the API reject a liquid/gas unit
  that contradicts Well type or Fluid Type, including the Well type fallback
  for a Sand Body whose Fluid Type is blank. The API validates Sand Bodies at
  the record level for this reason (see docs/devlog). A record missing Well
  type is rejected as incomplete, so its unit basis is never judged.
  The top Field/SI/Custom selector is derived and is never saved.
- Numeric controls show two decimal places when unfocused, or scientific
  notation for tiny nonzero values. Focusing reveals the full value, which
  is used for validation, conversion, JSON, CSV, and database storage.
- Hard-criterion choices (operating environment, severity, bean-up) show
  metric thresholds beside the original Field thresholds. Their stored option
  values stay as defined in the workbook.

## Sources for constants and terms

- [NIST Guide to the SI, Appendix B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8): foot, inch, pound, petroleum barrel, cubic foot, psi, bar, centipoise, temperature.
- [SLB oil FVF glossary](https://glossary.slb.com/terms/o/oil_formation_volume_factor) and [gas FVF glossary](https://glossary.slb.com/Terms/g/gas_formation_volume_factor.aspx): reservoir-volume-to-standard-volume definitions.
- [SLB Oilfield Review](https://www.slb.com/-/media/files/oilfield-review/1-unlocking--english.ashx): ppa as a pound of proppant added per gallon of fracturing fluid.
- [SLB mud density glossary](https://glossary.slb.com/terms/m/mud_density) and [equivalent circulating density glossary](https://glossary.slb.com/terms/e/equivalent_circulating_density): ppg density and its relation to pressure gradient.
- [Weatherford screen sizing table](https://www.weatherford.com/documents/catalog/gravel-pack-systems/): screen-gauge numbers alongside opening sizes, consistent with thousandths of an inch.
