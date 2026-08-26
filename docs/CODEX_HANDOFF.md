# Codex Handoff

## Checkpoint

| Field | Value |
|---|---|
| Repository branch | `implementation-v1` |
| Last committed checkpoint | `ecca57d checkpoint-phase0-3` |
| Current worktree | Clean after the Phase 0–3 checkpoint commit; `RESUME.txt` remains untouched and untracked |
| Completed scope | Phase 0, Phase 1, Phase 2, and Phase 3 only |
| Current data release | `2026.08-draft` / `DRAFT` |

## Phase status

- Phase 0: `DONE` — 21-file inventory, hashes, ZIP comparison, rule/source traceability, conflict log, owner checklist, and five audit tests.
- Phase 1: `DONE` — Pydantic reference-data contracts, units, manifest, strict CSV loader, cross-reference validation, immutable snapshot, migration contract, seed design-rule and BOQ-template datasets, and seven contract tests.
- Phase 2: `DONE` — snapshot-to-engine inverter catalogue adapter, model-specific DC/AC ratio handling, missing-limit preservation, pure inverter selection and AC-current trace records, and eight Phase 2 tests.
- Phase 3: `DONE` — typed protection candidates, Draft breaker source/status warnings, strict 70 °C ampacity assessment, correction-factor chain trace, grouping-factor boundary lookup, and seven Phase 3 tests.
- Phase 4–11: `FROZEN` — existing checkpoint artifacts remain untouched and are not evidence of completion.

## Phase 1 implementation record

Changed or added:

- `src/solar_design/models/units.py`
- `src/solar_design/models/schemas.py`
- `src/solar_design/models/manifest.py`
- `src/solar_design/models/migrations.py`
- `src/solar_design/models/snapshot.py`
- `src/solar_design/models/__init__.py`
- `src/solar_design/schemas/__init__.py`
- `src/solar_design/repositories/release.py`
- `src/solar_design/rules/defaults.py` — corrected invalid source IDs to the Phase 0 registry
- `data/releases/2026.08-draft/design_rules.csv`
- `data/releases/2026.08-draft/boq_templates.csv`
- `data/releases/2026.08-draft/manifest.json`
- `data/releases/2026.08-draft/inverters.csv` — corrected one malformed SG350HX-20 row width
- `scripts/build_release_manifest.py`
- `tests/phase1/test_data_contracts.py`

The loader validates UTF-8, duplicate headers, row widths, manifest hashes and counts, schema/data versions, Pydantic field constraints, per-dataset primary-key uniqueness, source foreign keys, BOQ rate links, and transformer-price rating links. CSV expression keys are checked against an explicit allow-list; arbitrary expression evaluation is not supported.

## Phase 2 implementation record

Changed or added:

- `src/solar_design/models/catalogue.py` — keeps AC voltage, phase configuration, and DC/AC ratio nullable when the reference row does not source them.
- `src/solar_design/models/results.py` — exposes the selected model ratio and nullable AC-current result for an unassessed circuit.
- `src/solar_design/calculations/inverter/catalogue.py` — pure adapters from `InverterRecord`/`ReferenceSnapshot` to the engine catalogue; no values are inferred.
- `src/solar_design/calculations/inverter/engine.py` — records model ratio separately from requested-to-installed AC ratio, rejects missing DC limits during normal eligibility, records override reasons, and returns `NOT_ASSESSED`-equivalent trace findings for missing AC voltage/phase.
- `src/solar_design/calculations/inverter/__init__.py`
- `src/solar_design/calculations/__init__.py`
- `tests/phase2/test_inverter_engine.py`

The `1.40` DC/AC ratio remains a per-record catalogue value. The engine never applies it globally. `SG350HX-20` is explicitly catalogued at `350 kW` AC (`352 kVA`), while it remains without a sourced maximum DC kWp and without a sourced ratio; normal DC-capacity selection rejects it, while an explicit owner override is retained as `USER_OVERRIDE` with a warning and no invented capacity. AC current uses a manufacturer maximum when available, otherwise a transparent fallback formula only when voltage and phase inputs exist.

## Phase 3 implementation record

Changed or added:

- `src/solar_design/models/catalogue.py` — immutable `CorrectionFactor`, `GroupingFactorSpec`, and `ProtectionCandidate` records with source/status metadata.
- `src/solar_design/calculations/ampacity/catalogue.py` — pure grouping-factor adapters and inclusive range lookup from `ReferenceSnapshot`.
- `src/solar_design/calculations/ampacity/engine.py` — strict 70 °C calculation, typed correction-factor chain, table-condition trace, source aggregation, and explicit unsourced-factor warnings.
- `src/solar_design/calculations/ampacity/__init__.py`
- `src/solar_design/calculations/protection/catalogue.py` — pure adapter for incomplete Draft breaker rows.
- `src/solar_design/calculations/protection/engine.py` — candidate trace interface that keeps Draft breaker data `NOT_ASSESSED` and never recommends a breaker without fault/coordination rules.
- `src/solar_design/calculations/protection/__init__.py`
- `src/solar_design/calculations/__init__.py`
- `tests/phase3/test_protection_ampacity.py`

The strict 70 °C formula returns `129.10 A` when rounded to two decimals for 100 A load, 90 °C cable, 40 °C ambient, and 70 °C terminal limit. Under the supplied Group 2 CV table rows, 25 mm² / 106 A fails and 35 mm² / 131 A passes. Grouping ranges are inclusive and overlapping/no-match ranges raise validation errors. Numeric correction factors remain accepted for compatibility but are explicitly marked unsourced; release-backed factors retain record ID, source IDs, conditions, and verification status in the audit trace.

## Verification

- `python -m pytest -p no:cacheprovider -q` — `27 passed`
- `python -m ruff check src/solar_design/models src/solar_design/calculations/inverter tests/phase2` — passed
- `python -m mypy src/solar_design/models src/solar_design/calculations/inverter tests/phase2` — passed
- `python -m compileall -q src tests/phase2` — passed
- Phase 3 scoped checks: `ruff` and `mypy` over `src/solar_design/models`, `src/solar_design/calculations/ampacity`, `src/solar_design/calculations/protection`, and `tests/phase3` — passed.
- `git diff --check` — passed; Git reported only existing line-ending normalization warnings.

## Known limitations and next action

- No engineering record is promoted to `VERIFIED`; owner approvals, utility requirements, and source licensing remain open.
- The data release is not approved for construction issue and is not a substitute for current manufacturer, standards, or utility documents.
- Existing wiring, transformer, BOQ, costing, export, and Streamlit code was not expanded in Phase 3.
- Protection remains assessment-only: all current breaker catalogue rows are `DRAFT`/`NOT_ASSESSED`, and no breaker is automatically selected until fault level, interrupting duty, terminal temperature, coordination, and utility rules are approved.
- Ampacity table rows and grouping factors remain `DRAFT` or `ASSUMPTION`; a mathematical PASS is not construction approval.
- A full-repository Mypy run still reports pre-existing out-of-scope typing errors in `boq/`, `costing/`, `exports/`, and Phase 1 test typing; those future-phase issues were not changed as part of this checkpoint. Phase 1–3 scoped Mypy passes.
- The current data release does not source nominal AC voltage, phase configuration, or maximum AC current for the inverter rows; therefore AC current can remain unassessed from the release snapshot and must not be guessed.
- The next authorized scope is Phase 4 cable/PE/conduit behavior after this handoff and the Phase 1–3 diff are reviewed. No Phase 4 implementation was started.

Before committing, stage only the Phase 1 through Phase 3 files listed above plus this handoff and the Phase 1 documentation/data changes. Do not stage `RESUME.txt` or unrelated Phase 4–11 artifacts.
