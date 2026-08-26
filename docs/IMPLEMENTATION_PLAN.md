# Implementation Plan — Solar Electrical Design & Cost Estimation

## Document control

| Field | Value |
|---|---|
| Document status | Draft for engineering-owner review |
| Application target | Production-quality Streamlit budgetary design tool for Thailand |
| Data release | `2026.08-draft` |
| Governing principle | One traceable workflow; no engineering formulas in Streamlit pages |
| Safety position | Budgetary estimate only; not an approved construction design |

## 1. Current source inventory

The audited baseline contains 21 files: 18 engineering/reference files under four numbered folders, plus `README.md`, `.gitignore`, and a ZIP reference snapshot. The ZIP contains the same 18 reference files byte-for-byte. The canonical Phase 0 inventory, byte sizes, and SHA-256 hashes for all 21 files are recorded in `data/releases/2026.08-draft/sources.csv`.

| Domain | Files | Current maturity |
|---|---:|---|
| Inverter | 2 PNG | Six product rows and one illustrative SLD; incomplete manufacturer data |
| 70 °C cable design | 5 JPG | Selected worked examples and excerpts; standards hierarchy unresolved |
| Cable / PE / conduit | 1 XLSX, 2 JPG, 1 PNG, 1 empty TXT | Prototype fill workbook and partial tables; not runtime-ready |
| Transformer / installation / BOQ | 1 Markdown, 4 PNG/JPG | Most complete requirements source; rules and prices remain draft |

There is no application package, test suite, dependency manifest, CI workflow, runtime master data, or approved engineering rule set in the audited baseline.

### Checkpoint boundary

The preceding sentence describes commit `14c6ec0`, the baseline that was audited. Checkpoint commit `24d986b` also contains partial Phase 1–9 implementation artifacts. They are not evidence that those phases are complete. Phase 1 now adds a validated manifest, Pydantic contracts, a loader, and contract tests, but `data/releases/2026.08-draft/` remains a DRAFT release and is not approved for construction use.

Phase 0 completion was limited to the three planning documents, the 21-row source registry, explicit rule-to-source links, conflict/owner-decision records, and automated repository-audit tests. Phase 1 data-contract work is recorded separately in `docs/CODEX_HANDOFF.md`; calculation behavior, Streamlit UI, and application tests remain later-phase work.

## 2. Product objective and workflow

The application shall implement one linked design workflow:

```text
Project Inputs / System Basis
  -> PV and load design
  -> Inverter selection
  -> AC current and protection candidate
  -> 70 °C ampacity check
  -> Phase/neutral cable selection
  -> PE conductor selection
  -> Discrete conduit allocation
  -> Transformer requirement and sizing
  -> Installation assessment
  -> Immutable DesignRun
  -> BOQ baseline plus user deltas
  -> Low/Base/High cost estimate
  -> Engineering summary and exports
```

The supported first release is a transparent budgetary estimator. Voltage drop, short-circuit withstand, protection coordination, utility compliance, and construction grounding design remain `NOT_ASSESSED` until approved rules and inputs exist.

## 3. Recommended architecture

Use a modular monolith with pure calculation engines and explicit ports for data and exports.

```text
app.py
src/solar_design/
  ui/                         # Streamlit pages, forms, adapters only
  domain/                     # Immutable value objects and aggregates
  models/                     # Pydantic persistence/input models
  calculations/
    inverter/
    protection/
    ampacity/
    wiring/
    transformer/
  rules/                      # Rule registry and executable policy mapping
  services/                   # Workflow orchestration and invalidation
  repositories/              # Validated CSV/JSON loaders
  boq/                        # Deterministic baseline and delta handling
  costing/                    # Decimal-based scenario cost engine
  audit/                      # Decisions, findings, overrides, events
  validation/                 # Schema, domain, workflow validation
  exports/                    # JSON, XLSX, CSV renderers
  schemas/                    # JSON Schema and migration definitions
data/releases/<data_version>/ # Immutable reviewed reference snapshots
assets/
tests/{unit,contract,integration,app,golden}/
docs/
.streamlit/config.toml
pyproject.toml
requirements.txt
```

### Architectural constraints

- UI modules must not contain engineering formulas, catalogue lookups, cost waterfalls, or quantity rules.
- Calculation functions accept typed inputs and an immutable reference snapshot and return typed outputs without importing Streamlit, pandas, filesystem APIs, clocks, or global state.
- CSV/JSON expressions are identifiers such as `STRICT_70C_EQUIVALENT_AMPACITY`; no arbitrary expression text is evaluated.
- Exports render an existing immutable run and never recalculate from mutable UI state.
- Unknown or draft evidence remains visible in the result, audit trail, and export.

### Public application interfaces

```python
run_design(project: ProjectRevision, refs: ReferenceSnapshot) -> DesignRun
select_inverters(request, catalogue, rules) -> InverterSelection
calculate_ac_circuits(selection, system_basis) -> list[CircuitRequirement]
select_protection(circuit, catalogue, rules) -> ProtectionSelection
check_70c_ampacity(circuit, installation, tables, factors) -> AmpacityAssessment
select_cables_and_pe(circuit, assessment, catalogues, rules) -> WiringSelection
allocate_conduits(cables, conduits, fill_rules) -> ConduitAllocation
size_transformer(request, catalogue, rules) -> TransformerSelection
generate_boq(run, template, prior_deltas=None) -> BOQRevision
calculate_cost(boq, rates, policy) -> CostRevision
```

## 4. Calculation dependency and invalidation

`SystemBasis` fixes utility, phase arrangement, frequency, grid voltage, collection voltage, and transformer duty. A change to any upstream input marks every dependent result `STALE`. Recalculation creates a new `DesignRun` with `parent_run_id`; it does not mutate the prior result.

| Changed input | Invalidated outputs |
|---|---|
| PV kWp, inverter choice, quantity | AC circuits onward |
| Voltage, phase, PF, efficiency | AC current, protection, wiring, transformer, BOQ, cost |
| Breaker selection/settings | Ampacity and wiring onward |
| Installation method, ambient, grouping | Ampacity and wiring onward |
| Cable choice/count/OD | PE, conduit, BOQ, cost |
| Transformer count/duty/rating | currents, installation, BOQ, cost |
| BOQ user delta | cost and exports only |
| Rate snapshot or percentage policy | cost and exports only |

## 5. Streamlit navigation and state

Use `st.navigation` and `st.Page` with these pages:

1. Dashboard
2. Project & System Basis
3. PV / Inverter Selection
4. Protection & 70 °C Ampacity
5. Cable / PE / Conduit
6. Transformer & Installation
7. BOQ Editor
8. Cost Summary
9. Assumptions & Audit
10. Master Data
11. Export

`st.session_state` holds one `WorkspaceState` aggregate:

- `ProjectDraft`: current form values.
- `ProjectRevision`: immutable validated input snapshot and input hash.
- `ReferenceSnapshot`: data release, source IDs, and file hashes.
- `DesignRun`: engine outputs, findings, decisions, and status.
- `BOQRevision`: generated baseline plus explicit user deltas.
- `CostRevision`: rate snapshot, scenario totals, and warnings.

PEA is the initial utility profile. MEA and Other remain selectable but issue an unsupported-profile warning. Strict 70 °C is the default terminal-temperature policy. Draft and unknown rules permit budgetary continuation with visible warnings; manual deviation from a recommendation requires an override reason.

## 6. Engineering audit trail

Each engine emits append-only `DecisionRecord` entries containing:

- engine, rule ID, rule revision, and expression key;
- normalized inputs and units;
- formula parameters and intermediate values;
- calculated value and selected value;
- candidates and rejection reasons;
- source IDs and verification status;
- findings and severity;
- override ID, actor, timestamp, and mandatory reason;
- application version, data version, data hashes, and input hash.

Finding severities are `BLOCKER`, `WARNING`, `REVIEW`, and `INFO`. Schema failures, negative values, invalid PF/derating, broken references, model/CSA mismatch, and missing mandatory inputs are blockers. Unapproved engineering rules are warnings or review holds and must never be relabelled as verified by calculation success.

## 7. BOQ and costing design

The BOQ generator consumes only a `DesignRun` and a versioned template. Generated line IDs are deterministic. Regeneration preserves user changes as deltas (`ADD`, `UPDATE`, `EXCLUDE`, `RESTORE`) against the baseline.

Pricing modes are mutually exclusive:

- `COMPOSITE`: amount = quantity × unit price.
- `BREAKDOWN`: amount = quantity × (material + labor + equipment).

`EXCL` lines remain visible and are omitted from totals. `PS` enters totals only when it has a provisional value. Duplicate-scope groups detect potential double charging for crane, transport, testing, and ground conductor included with rods.

Use `Decimal` and round each line and each waterfall layer to THB 0.01:

```text
Direct Cost = included BOQ line amounts
Preliminaries = Direct Cost × preliminaries rate
OH&P = (Direct Cost + Preliminaries) × OH&P rate
Contingency = (Direct Cost + Preliminaries + OH&P) × contingency rate
Subtotal before VAT = Direct Cost + Preliminaries + OH&P + Contingency
VAT = Subtotal before VAT × VAT rate
Grand Total = Subtotal before VAT + VAT
```

Low/Base/High values are read directly from rates. When Low or High is absent, reuse Base only for budget continuity and emit `SINGLE_POINT_PRICE`. A missing Base price remains missing and requires manual input.

## 8. Export architecture

- JSON is the canonical project package and includes schema/data versions, hashes, all revisions, warnings, assumptions, and overrides. Unknown fields and incompatible versions fail safely.
- Excel contains Project Information, Design Calculation, BOQ, Cost Summary, Unit Rates, Transformer Prices, Assumptions, and Sources. Python results are canonical; spreadsheet formulas are reconciliation aids only.
- CSV supports BOQ and master-data interchange with UTF-8 encoding and strict schema validation.
- PDF is deferred until Thai font embedding and visual verification are approved.

All engineering and cost outputs display the Thai budgetary disclaimer from the transformer specification.

## 9. Testing strategy

### Unit and contract tests

- Table-driven tests for every formula, lookup, threshold, and status transition.
- Property tests: increasing load cannot reduce required capacity; selected standard rating cannot be below required kVA; accepted conduit fill cannot exceed the count-specific limit.
- Data-contract tests for headers, types, status enums, stable IDs, uniqueness, source references, effective dates, and manifest hashes.
- Golden tests tied to approved hand calculations and source revisions.

### Critical engineering cases

- 100 A, 90 °C cable, 40 °C ambient, strict 70 °C: required table ampacity `129.10 A`.
- Group 2, three loaded 1-core conductors: 25 mm² / 106 A fails; 35 mm² / 131 A passes.
- 125% method yields approximately 72 °C and therefore fails a strict 70 °C criterion.
- Blank cable row returns `EMPTY/REVIEW`; broken OD returns `MISSING`; model/CSA mismatch blocks.
- Parallel conduits allocate whole cable pieces and reject a 3+2 split if either conduit exceeds its limit.
- 500 kVA at 22 kV returns approximately 13.12 A; at 400 V returns approximately 721.69 A.
- Required 3,001 kVA returns out-of-range and no automatic selection.
- Cost example: THB 100,000 direct with 5% preliminaries, 10% OH&P, 5% contingency, and 7% VAT returns THB 129,764.25.

### Integration and AppTest

- Full workflow across all four engines, staleness after upstream edits, and deterministic recalculation.
- Multipage navigation, rerun-safe state, form validation, warning visibility, mandatory override reason, editable BOQ, upload rejection, and downloads.
- JSON migration/round-trip, Excel sheet/formula/value reconciliation, Thai text, missing-image fallback, and Community Cloud smoke test.

## 10. Development phases

| Phase | Objective and principal changes | Dependencies / rules | Required tests | Definition of done |
|---|---|---|---|---|
| 0 — Repository audit | Publish these three docs, 21-row source registry, hashes, ZIP comparison, conflicts, and owner checklist | None | Inventory, hashes, ZIP duplicate, rule-source links | Every known rule is classified; owner gaps are explicit; Phase 0 audit tests pass |
| 1 — Domain/data models | Create package, enums, Pydantic models, units, schemas, loaders, manifests, migrations | Phase 0 | Schema, uniqueness, references, round-trip | All seed records validate with no orphan source |
| 2 — Inverter engine | Catalogue eligibility, fleet selection, circuit outputs, trace records | Phase 1; model-specific DC limits | Ratio, missing limits, override tests | SG350 receives no inferred kWp; results are typed and traced |
| 3 — Protection/ampacity | Protection candidate interface, correction chain, strict 70 °C engine | Phases 1–2 | 129.10 A example, table boundaries, grouping | Each result cites table conditions and factor chain |
| 4 — Cable/PE/conduit | Cable/PE lookup and integer conduit allocation | Phase 3; PE rule remains draft | Broken references, blanks, mismatch, discrete allocation | No false pass and no silent OD/PE fabrication |
| 5 — Transformer | Load/PV sizing, standard selection, currents, duty modes, installation assessment | Phases 1–4 | Current examples, boundaries, 3,001 kVA, equal/N-1 | Deterministic sizing and explicit approval status |
| 6 — BOQ | Template evaluator, deterministic baseline, delta merge, duplicate-scope findings | Design outputs | Idempotence, all cost statuses, duplicates | Regeneration preserves user changes |
| 7 — Costing | Decimal low/base/high waterfall and price-validity handling | Phase 6 | Waterfall, rounding, missing/single price | Totals reconcile and warnings are complete |
| 8 — Streamlit UI | Pages, typed state coordinator, theme, assets, stale-state behavior | Phases 1–7 | AppTest navigation, state, validation, overrides | End-to-end project-to-cost flow without formulas in UI |
| 9 — Export | JSON, Excel, CSV and import validation | Phase 8 | Round-trip, sheet structure, Thai text, reconciliation | Snapshot can be reproduced without recalculation |
| 10 — Verification | Golden/property/integration suites, CI, packaging, security checks | Phases 1–9 | Full suite and Linux smoke test | No software blockers; supported engineering scope has no hidden unknowns |
| 11 — UX/release | Thai/English refinement, accessibility, help, deployment guide, pilot release | Phase 10 | Tablet/manual smoke and AppTest | Restricted pilot is versioned and rollback-ready |

## 11. Major risks and owner decisions

Engineering owner approval is required for:

1. Governing standards, editions, hierarchy, and redistribution rights.
2. PEA/MEA installation eligibility, voltage classes, and transformer limits.
3. Inverter datasheets, maximum AC current, DC voltage/MPPT limits, and DC/AC policy.
4. Breaker AT/AF, breaking capacity, fault level, and coordination policy.
5. Cable installation methods, complete ampacity/correction tables, voltage-drop limits, short-circuit duty, harmonics, and parallel-cable policy.
6. The source and applicability of the PE `S/2` mapping.
7. Certified conduit IDs, cable ODs, bending, pulling, and allocation requirements.
8. Ground resistance target, soil data, electrode/conductor details, and two-transformer topology.
9. Transformer impedance, losses, reverse-power duty, utilization/oversize threshold, and redundancy policy.
10. Quotations, validity, commercial inclusions, quantity rules, Low/High rates, VAT defaults, and approval/signature workflow.

Until these decisions are approved, this data release must retain the suffix `draft`, contain no `VERIFIED` records, and remain unsuitable for construction issue.
