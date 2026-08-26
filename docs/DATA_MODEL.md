# Data Model — Release `2026.08-draft`

## Phase 0 implementation boundary

This document is the proposed data contract, not a claim that Phase 1 is complete. In Phase 0, only `sources.csv` is an audit-controlled registry. The other CSV extracts present in the checkpoint are preliminary inputs retained for later review. `manifest.json`, `design_rules.csv`, and `boq_templates.csv` do not yet exist; creating and validating them belongs to Phase 1. Consequently, the current directory must not be loaded or described as an approved runtime `ReferenceSnapshot`.

## 1. Versioning and common record contract

All seed files are UTF-8 CSV except `manifest.json`. Data records use stable uppercase IDs and carry:

- `record_id`: immutable primary key.
- `schema_version`: schema contract version, initially `1.0.0`.
- `data_version`: immutable release ID, `2026.08-draft`.
- `revision`: positive integer row revision.
- `verification_status`: controlled engineering status.
- `source_id`: foreign key to `sources.csv`; multiple IDs use `|`.
- `effective_from`, `effective_to`: ISO dates; blank means unknown, not perpetual.
- `notes`: concise uncertainty/applicability statement.

Allowed verification statuses are `DRAFT`, `ASSUMPTION`, `MANUFACTURER_DATA`, `UTILITY_REQUIREMENT`, `REQUIRES_UTILITY_APPROVAL`, `USER_OVERRIDE`, `UNKNOWN`, and `NOT_PERMITTED`. This release intentionally has no `VERIFIED` rows.

CSV empty fields deserialize to `None`; they must never become zero, false, or an empty engineering approval. Tri-state commercial flags use `YES`, `NO`, or blank/unknown.

## 2. Reference-data schemas

### `sources.csv`

Primary key `source_id`. Fields cover title, issuer, source type, edition/date, locator, repository-relative path, SHA-256, byte size, authority class, licensing status, review status, reviewer, review date, and notes. A source record being present does not make its engineering content verified.

### `inverters.csv`

Key fields: manufacturer, model, AC kW/kVA, voltage, phases, PF limits, nominal/max AC current, recommended maximum DC kWp, MPPT/input current information, ambient reference, and derating profile. Missing SG350HX-20 DC kWp is null and blocking for a final DC-array recommendation. Model-specific 1.40 ratios are stored as data, not a global rule.

### `cables.csv`

Key fields: system, manufacturer, family, model, conductor material, insulation, voltage class, core count, CSA, OD, OD basis, conductor-temperature rating, and intended use. Workbook PV rows with broken `#REF!` OD remain null/`UNKNOWN`. No cable row itself proves ampacity suitability.

### `ampacity.csv`

Each row identifies table/family, material, insulation, conductor temperature, installation group/method, core/loading condition, CSA, ampacity, reference ambient, and applicability. Only explicitly extracted sample rows are seeded; this file is not a complete national ampacity table.

### `grouping_factors.csv`

Rows identify installation family, minimum and maximum circuit-group counts, factor, counting basis, and conditions. Group-count ranges are inclusive. A one-group factor of 1.0 is marked `ASSUMPTION`; supplied multi-group values are `DRAFT`.

### `pe_mapping.csv`

Maps phase CSA to PE CSA for listed copper sizes only. Exact lookup is required. Inputs outside the table return `UNKNOWN`; interpolation/extrapolation is prohibited.

### `breakers.csv`

Contains placeholders reconstructed from the example SLD. Manufacturer/model, breaking capacity, voltage rating, poles, terminal rating, and coordination data are null. Records cannot support final protection selection.

### `conduits.csv`

Contains Panasonic IMC catalogue dimensions transcribed from the workbook. `screening_internal_diameter_mm = outside_diameter_mm - 2 × minimum_wall_mm`; `screening_internal_area_mm2 = πd²/4`. These are screening values, not certified actual IDs.

### `transformers.csv`

Contains the complete draft standard-rating list. Generic rows have no manufacturer/model and do not assert availability, utility acceptance, vector group, impedance, or loss class. HV/LV catalogue matching belongs to quoted product/price records.

### `transformer_prices.csv`

Price identity is manufacturer + rating + HV + LV + quotation. Price is THB/unit and VAT exclusion is explicit. Commercial inclusion flags remain null when unknown. Alternative ratings/voltages are independent options and must never be summed as a catalogue total.

### `unit_rates.csv`

Includes item code, BOQ category, Thai/English descriptions, unit, Low/Base/High values, currency, source date, included/excluded scope, and duplicate-scope group. Low/High stay null when not supplied. Hipot and hotline Base values stay null.

### `design_rules.csv`

Stores `domain`, `rule_type`, applicability selectors, `expression_key`, JSON-encoded parameters, outcome, severity, override policy, and source trace. `expression_key` maps to reviewed Python code; runtime evaluation of arbitrary expressions is forbidden.

### `boq_templates.csv`

Stores installation type, condition key, BOQ item/category, description, quantity-rule key, default quantity/unit, rate item link, pricing mode, cost status, duplicate-scope group, editability, and display order. Missing quantities or rates create editable provisional lines rather than fabricated totals.

## 3. Runtime domain aggregates

### Project and reference state

```text
WorkspaceState
 ├─ ProjectDraft
 ├─ ProjectRevision (immutable, input_hash)
 ├─ ReferenceSnapshot (data_version, manifest_hash, source hashes)
 ├─ DesignRun (immutable, parent_run_id, freshness)
 ├─ BOQRevision (baseline + deltas)
 └─ CostRevision (rate snapshot + scenarios)
```

`ProjectRevision` includes identity, client/site, utility, purpose, phase/frequency, MV/LV voltage, transformer count/duty, load/PV data, PF, demand/spare/derating, route/install conditions, environmental flags, and assumptions.

`ReferenceSnapshot` records the exact files and hashes loaded. A changed data release requires a new design run.

### Design outputs

- `InverterSelection`: requested DC/AC basis, selected model quantities, eligibility findings, total AC kW/kVA, and source trace.
- `CircuitRequirement`: circuit ID, equipment source, voltage/phase, current basis, calculated/design current, PF/efficiency, and fallback flag.
- `ProtectionSelection`: candidate/selected device, trip/frame data, unresolved ratings, and coordination status.
- `AmpacityAssessment`: required table ampacity, correction chain, candidate cable, pass/fail, and terminal-temperature policy.
- `WiringSelection`: phase/neutral/PE conductors, parallel runs, cable count, conduit allocations, and unassessed checks.
- `TransformerSelection`: required kVA, selected total/per-unit rating, duty mode, HV/LV currents, utilization, installation status, and approval findings.

Every output holds `decision_ids` and `finding_ids`; no human-readable warning is the sole copy of audit information.

## 4. Audit, findings, and overrides

`DecisionRecord` fields:

```text
decision_id, run_id, engine, rule_id, rule_revision, expression_key,
inputs[{name,value,unit}], intermediates[], calculated_value,
selected_value, candidates[], rejection_reasons[], source_ids[],
verification_status, finding_ids[], override_id, application_version,
data_version, input_hash, created_at
```

`Finding` fields: `finding_id`, code, severity, domain, message TH/EN, affected object IDs, rule/source IDs, resolution guidance, resolved flag, and resolution reference.

`Override` fields: `override_id`, affected decision, recommended value, selected value, reason, actor, timestamp, status=`USER_OVERRIDE`, and reviewer/approval fields. Blank reasons are invalid.

## 5. BOQ and cost revisions

`BOQRevision` contains immutable generated lines and append-only deltas. Each line has quantity, unit, one pricing mode, cost status, source, assumptions, duplicate group, and generated/manual provenance.

`CostRevision` contains rate snapshot ID, currency, scenario, direct-category totals, preliminaries, OH&P, contingency, subtotal, VAT, grand total, line-level rounding policy, and warnings. Money uses `Decimal`; floating point is not canonical.

## 6. Manifest and validation

`manifest.json` declares schema/data version, release status/date, application compatibility, status enum, dataset filename/record count/SHA-256, source inventory count, approver state, and known limitations. It does not hash itself.

Loader validation order:

1. Decode UTF-8 and reject duplicate headers.
2. Validate manifest schema/version compatibility and file hashes.
3. Validate row types, enum values, units, dates, and non-negative numeric fields.
4. Enforce primary-key uniqueness and source/rate foreign keys.
5. Enforce dataset rules: exact transformer price identity, no false confirmed conduit ID, no missing OD treated as zero, and no arbitrary expression keys.
6. Build an immutable `ReferenceSnapshot`; any blocker rejects the release.

## 7. Compatibility and migrations

- Patch-level data corrections retain schema `1.0.0`, increment row revision, and create a new immutable data release.
- Additive optional columns require a schema minor version.
- Renamed/removed columns, changed units, enum semantics, or calculation meaning require a major schema version and explicit migration.
- Project JSON imports migrate version by version; unknown future major versions fail with a user-readable error.
- Stable IDs are never recycled, even when a row is superseded.
