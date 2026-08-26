# Engineering Rule Matrix

## Status and enforcement model

This matrix records what the repository supports, not what an external standard may require. Release `2026.08-draft` intentionally contains no `VERIFIED` rules.

| Status | Meaning | Runtime behavior |
|---|---|---|
| `DRAFT` | Extracted or proposed rule pending engineering review | Calculate for budget use; show warning and source |
| `ASSUMPTION` | Derived or selected implementation policy | Show assumption; require review when material |
| `MANUFACTURER_DATA` | Product-style value without an approved/current datasheet package | Enforce stated hard limit only within documented applicability; warn on provenance |
| `UTILITY_REQUIREMENT` | Utility-issued requirement with identified authority | Reserved; no current rows qualify |
| `REQUIRES_UTILITY_APPROVAL` | Decision cannot be finalized without owning utility | Allow budget path; hold final recommendation |
| `USER_OVERRIDE` | User-selected departure with retained reason | Preserve original and overridden value |
| `UNKNOWN` | Evidence is absent, broken, or too ambiguous | Never infer a fixed rule; return missing/not assessed |
| `NOT_PERMITTED` | Explicit prohibition from an approved source | Block; no current rows qualify |

Finding severities are independent: `BLOCKER`, `WARNING`, `REVIEW`, and `INFO`.

## Rule-to-source registry

These links identify repository provenance only; they do not upgrade a rule's verification status. Where an implementation policy was introduced to correct or safely bound a prototype, the linked source is the artifact that created the need for that policy.

| Rule IDs | Source IDs | Traceability note |
|---|---|---|
| INV-001, INV-002, INV-003, INV-004, INV-005, INV-006, INV-007, INV-008, INV-009 | SRC-INV-001 | Product values and the model-specific ratio/fallback context |
| INV-010 | SRC-INV-002 | Illustrative SLD only |
| AMP-001, AMP-002, AMP-003, AMP-004, AMP-005 | SRC-AMP-001, SRC-AMP-002, SRC-AMP-003, SRC-AMP-004, SRC-AMP-005 | The five-slide thermal-design evidence set is incomplete and must be reviewed together |
| AMP-006 | SRC-WIR-005 | Selected buried-XLPE table excerpt |
| AMP-007, AMP-008, AMP-009 | SRC-WIR-004 | Selected grouping-factor excerpt and its stated exceptions |
| PRO-001, PRO-002 | SRC-INV-002 | SLD labels expose candidates and missing protection evidence |
| CAB-001, CAB-002, CAB-003 | SRC-WIR-003 | Workbook catalogue and validation defects |
| PE-001 | SRC-WIR-002 | Image mapping only |
| PE-002 | SRC-WIR-001, SRC-WIR-002 | Empty text file plus partial image demonstrate missing scope |
| CON-001, CON-002, CON-003, CON-004 | SRC-WIR-003 | Workbook fill rules and screening limitations |
| TRF-001, TRF-002, TRF-003, TRF-004, TRF-005, TRF-006, TRF-007 | SRC-TRF-001 | Draft transformer estimator specification |
| INS-001, INS-002 | SRC-TRF-001, SRC-TRF-002, SRC-TRF-003 | Specification and installation illustrations; no utility eligibility table |
| YARD-001, YARD-002, YARD-003 | SRC-TRF-001, SRC-TRF-005 | One-transformer draft quantities and drawing |
| YARD-004, YARD-005, YARD-006, YARD-007 | SRC-TRF-001, SRC-TRF-006 | Two-transformer draft quantities and missing bands |
| GND-001, GND-002, GND-003 | SRC-TRF-001, SRC-TRF-004, SRC-TRF-005, SRC-TRF-006 | Draft grounding guidance and unresolved topology |
| BOQ-001, BOQ-002, BOQ-003, BOQ-004 | SRC-TRF-001 | Draft BOQ requirements and scope conflicts |
| CST-001, CST-002, CST-003, CST-004, CST-005 | SRC-TRF-001 | Draft prices plus owner-pending costing policies |

## Inverter and AC-current rules

| Rule ID | Rule / source evidence | Status | Implementation treatment |
|---|---|---|---|
| INV-001 | SG36CX-P2: 36 kW AC and 50.4 kWp recommended maximum PV input | `MANUFACTURER_DATA` | Model-specific limit; source image lacks datasheet revision |
| INV-002 | SG40CX-P2: 40 kW and 56.0 kWp | `MANUFACTURER_DATA` | Same treatment |
| INV-003 | SG50CX-P2: 50 kW and 70.0 kWp | `MANUFACTURER_DATA` | Same treatment |
| INV-004 | SG125CX-P2: 125 kW and 175.0 kWp | `MANUFACTURER_DATA` | Same treatment |
| INV-005 | SG150CX: 150 kW and 210.0 kWp | `MANUFACTURER_DATA` | Same treatment |
| INV-006 | The first five rows imply DC/AC = 1.40 | `ASSUMPTION` | Never apply globally; retain on each applicable model row |
| INV-007 | SG350HX-20: 350 kW, 352 kVA at 30 °C | `MANUFACTURER_DATA` | Do not extrapolate to another ambient temperature |
| INV-008 | SG350HX-20 lists `6 × 75 A` maximum DC input but no recommended kWp | `MANUFACTURER_DATA` / `UNKNOWN` | Block final DC-array recommendation until topology and voltage data exist |
| INV-009 | Prefer manufacturer maximum AC output current; fallback `I=P/(sqrt(3)·V·PF·efficiency)` or `I=S/(sqrt(3)·V)` | `ASSUMPTION` | Fallback use must be visible in audit |
| INV-010 | Example SLD likely represents `2×350 + 1×36 = 736 kW` at 400 V | `ASSUMPTION` | Test/illustration only; never default project topology |

## Protection, ampacity, cable, PE, and conduit rules

| Rule ID | Rule / source evidence | Status | Implementation treatment |
|---|---|---|---|
| AMP-001 | Strict 70 °C conversion: `Ir = Io / sqrt((θo-θa)/(θr-θa))` | `DRAFT` | Default policy pending standards approval |
| AMP-002 | 100 A, θr=70 °C, θo=90 °C, θa=40 °C gives 129.10 A required table ampacity | `DRAFT` | Golden test |
| AMP-003 | Group 2, 3 loaded 1-core CV: 25 mm²=106 A fails; 35 mm²=131 A passes | `DRAFT` | Applicable only to the stated table conditions |
| AMP-004 | PVC 70 °C alternative, same stated Group 2 condition: 35 mm²=96 A; 50 mm²=117 A | `DRAFT` | Separate table/policy path |
| AMP-005 | `125%` / 80% loading method gives about 72 °C in the supplied example | `ASSUMPTION` | Must fail strict 70 °C; do not treat as equivalent |
| AMP-006 | Buried XLPE 35 mm² examples: Group 5/2 conductors=150 A, Group 5/3=132 A, Group 6/≤3=184 A at 30 °C | `DRAFT` | Seed-only rows; table is incomplete |
| AMP-007 | Grouping factors by circuit-group count are recorded in `grouping_factors.csv` | `DRAFT` | Apply only to matching installation family and notes |
| AMP-008 | Single-core grouping count may be `n/2` for single-phase or `n/3` for three-phase | `DRAFT` | Preserve fractional-to-group rounding policy for owner approval |
| AMP-009 | Certain ≤3 m underground entry/exit sections may avoid grouping derating | `DRAFT` | Requires all source conditions; no automatic exemption in v1 |
| PRO-001 | Example labels resemble 63/75 A, 540/600 A, and 1063/1250 A calculated/trip/frame pairs | `DRAFT` | Placeholder records only; no breaking-capacity or coordination recommendation |
| PRO-002 | Breaking capacity, fault level, settings, selectivity, and terminal rating are missing | `UNKNOWN` | Report `NOT_ASSESSED`; never select final protection |
| CAB-001 | Cable OD catalogue entries in workbook support physical-fill screening | `MANUFACTURER_DATA` | Four PV ODs are broken and remain null; all records require current catalogue verification |
| CAB-002 | Model/CSA mismatch is a hard validation error | `ASSUMPTION` | Block calculation; never trust free-text model alone |
| CAB-003 | Blank model or zero-quantity row is empty/review, not pass | `ASSUMPTION` | Prevent workbook regression |
| PE-001 | Static PE mapping includes 35→25 through 400→240 mm² | `DRAFT` | Lookup only for listed Cu rows; no extrapolation |
| PE-002 | PE sizes below 35 mm², above 400 mm², other materials, and adiabatic duty are absent | `UNKNOWN` | Return missing/review |
| CON-001 | Raceway fill: one cable 53%, two cables 31%, three or more 40% | `DRAFT` | Cable count means physical pieces |
| CON-002 | `ID = OD - 2×minimum wall`; area=`πID²/4` | `ASSUMPTION` | Screening only; certified ID required before issue for construction |
| CON-003 | Parallel raceways must allocate whole cable pieces and validate each raceway | `ASSUMPTION` | No fractional-area division |
| CON-004 | Bending radius, pulling tension, raceway bends, and mechanical constraints are missing | `UNKNOWN` | Report `NOT_ASSESSED` |

## Transformer and installation rules

| Rule ID | Rule / source evidence | Status | Implementation treatment |
|---|---|---|---|
| TRF-001 | Load sizing: `kVA = load kW × demand factor / PF × (1+spare) / derating` | `DRAFT` | Validate PF and derating in `(0,1]` |
| TRF-002 | Three-phase full-load current: `I = kVA×1000/(sqrt(3)×V)` | `DRAFT` | Three-phase only |
| TRF-003 | Standard ratings 30–3,000 kVA | `DRAFT` | Select smallest rating ≥ required; above range returns no selection |
| TRF-004 | Solar sizing uses total inverter AC power, PF, and design margin | `UNKNOWN` | Exact formula/export basis requires owner decision |
| TRF-005 | Single-phase current formula is not supplied | `UNKNOWN` | Restrict automatic current result to three phase until approved |
| TRF-006 | Two transformers support Equal Load Sharing or N-1; Equal is product default | `ASSUMPTION` | Display duty mode and per-unit/total basis |
| TRF-007 | Oversize warning threshold is unspecified | `UNKNOWN` | Show utilization; no oversize judgment until configured |
| INS-001 | Canonical types are Yard, Pole Mounted, and Platform/H-frame | `DRAFT` | Do not merge pole and platform in rules/BOQ |
| INS-002 | No sourced decision table selects installation type by rating/utility | `UNKNOWN` / `REQUIRES_UTILITY_APPROVAL` | User selection requires warning and reason |
| YARD-001 | One unit, 315–630 kVA: pad 1.5×2.5 m, yard 4×4.5 m, 30 m earth conductor, 5 rods | `DRAFT` | Budget quantity only |
| YARD-002 | One unit, 1,000–1,250 kVA: pad 2×3 m, yard 4.5×4.5 m, 32 m, 5 rods | `DRAFT` | Budget quantity only |
| YARD-003 | One unit, 1,500–2,000 kVA: pad 2.5×3.5 m, yard 5×5 m, 34 m, 5 rods | `DRAFT` | Budget quantity only |
| YARD-004 | Two units, each 315–630 kVA: pad 1.5×5 m, yard 4×7 m, 35 m, 5 rods | `DRAFT` | Budget quantity only |
| YARD-005 | Two units, each 1,000–1,250 kVA: pad 2×6 m, yard 4.5×8 m, 38 m, 5 rods | `DRAFT` | Budget quantity only |
| YARD-006 | Two units, each 1,500–2,000 kVA: pad 2.5×7 m, yard 5×9 m, 42 m, 5 rods | `DRAFT` | Budget quantity only |
| YARD-007 | Other rating/count bands are not supplied | `UNKNOWN` | Require manual dimensions and review; no interpolation |
| GND-001 | Yard uses five initial rods; one MDB rod is additional | `DRAFT` | Quantity estimate only |
| GND-002 | Actual electrodes depend on soil resistivity and resistance testing | `REQUIRES_UTILITY_APPROVAL` | Mandatory construction-design hold point |
| GND-003 | Two-transformer neutral-electrode topology is absent | `UNKNOWN` | Flag; do not infer six/seven rods |

## BOQ and costing rules

| Rule ID | Rule / source evidence | Status | Implementation treatment |
|---|---|---|---|
| BOQ-001 | Generate by installation type and keep user edits | `DRAFT` | Deterministic baseline plus deltas |
| BOQ-002 | Cost statuses are F, V, O, PS, EXCL | `DRAFT` | EXCL omitted; PS included only with value |
| BOQ-003 | Prevent duplicate crane/transport when included in transformer quote | `DRAFT` | Tri-state scope flags and duplicate groups |
| BOQ-004 | Ground-rod rate says cable included while yard rules quantify conductor separately | `UNKNOWN` | Emit duplicate-scope review warning |
| CST-001 | Transformer prices are THB excluding VAT | `DRAFT` | Exact manufacturer/rating/HV/LV matching only |
| CST-002 | Missing transformer price cannot be silently estimated | `DRAFT` | Manual price required and retained as override |
| CST-003 | Supplied rates are single-point; Low/High are absent | `DRAFT` | Reuse Base with `SINGLE_POINT_PRICE` warning only |
| CST-004 | Sequential percentage waterfall in implementation plan | `ASSUMPTION` | Owner must approve percentage bases |
| CST-005 | Amount uses Composite or Breakdown mode, never both | `ASSUMPTION` | Block double-counting configuration |

## Conflicts and missing information

1. The source set mixes Thai, BS 7671, and AS/NZS references without an approved edition or precedence hierarchy.
2. Strict 70 °C and the 125% method produce different acceptance outcomes.
3. The conduit workbook has 48 propagated `#REF!` cells, incorrectly treats blank rows as pass, and uses fractional parallel allocation.
4. Screening conduit IDs are duplicated into a field labelled confirmed actual ID.
5. The PE mapping lacks source edition, applicability, smaller sizes, and fault-duty checks.
6. The SLD breaker/cable/raceway annotations are not legible or labelled sufficiently for design rules.
7. No utility installation decision table, protection/metering arrangement, or approved grounding criterion is supplied.
8. Yard design bands omit 30–250, 800, 2,500, and 3,000 kVA and must not be interpolated.
9. Grounding guidance covers one-transformer neutral detail only; the two-transformer arrangement is unresolved.
10. Yard rate descriptions do not match the six draft yard dimensions.
11. Quotations lack quotation numbers, validity dates, and delivery/crane/installation/testing/inspection scope flags.
12. Low/High prices and most detailed quantity rules are absent.

## Owner-confirmation checklist

- [ ] Approve governing standards, editions, hierarchy, and data redistribution rights.
- [ ] Supply current inverter datasheets and approve DC/AC and AC-current policies.
- [ ] Approve breaker, fault-level, coordination, and terminal-temperature rules.
- [ ] Approve complete ampacity/correction tables and cable installation methods.
- [ ] Approve voltage-drop, short-circuit, neutral/harmonic, and parallel-cable criteria.
- [ ] Confirm PE rule source and adiabatic/minimum-size precedence.
- [ ] Confirm certified conduit IDs, cable ODs, and mechanical installation criteria.
- [ ] Supply PEA/MEA installation eligibility and approval workflow.
- [ ] Approve transformer duty, utilization, losses, impedance, and redundancy policies.
- [ ] Approve grounding resistance, soil, conductor, electrode, and testing criteria.
- [ ] Supply quotation documents, validity, scope flags, and Low/High pricing policy.
- [ ] Approve BOQ quantity rules, duplicate-scope policy, and cost waterfall bases.
