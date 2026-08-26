# Codex Handoff

## Checkpoint

| Field | Value |
|---|---|
| Repository branch | `implementation-v1` |
| Last committed checkpoint | `1e689db checkpoint-handoff-phase0-3` |
| Current worktree | Contains the Phase 4–11 implementation and tests from this handoff; pre-existing `desktop.ini` remains untracked |
| Completed scope | Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9, Phase 10, and Phase 11 |
| Current data release | `2026.08-draft` / `DRAFT` |

## Phase status

- Phase 0: `DONE` — 21-file inventory, hashes, ZIP comparison, rule/source traceability, conflict log, owner checklist, and five audit tests.
- Phase 1: `DONE` — Pydantic reference-data contracts, units, manifest, strict CSV loader, cross-reference validation, immutable snapshot, migration contract, seed design-rule and BOQ-template datasets, and seven contract tests.
- Phase 2: `DONE` — snapshot-to-engine inverter catalogue adapter, model-specific DC/AC ratio handling, missing-limit preservation, pure inverter selection and AC-current trace records, and eight Phase 2 tests.
- Phase 3: `DONE` — typed protection candidates, Draft breaker source/status warnings, strict 70 °C ampacity assessment, correction-factor chain trace, grouping-factor boundary lookup, and seven Phase 3 tests.
- Phase 4: `DONE` — release adapters for cable/PE/conduit data, exact PE lookup, hard model/CSA validation, missing/broken OD handling, and whole-cable conduit allocation using 53%/31%/40% fill limits, with seven Phase 4 tests.
- Phase 5: `DONE` — Decimal transformer load/PV sizing, HV/LV three-phase currents, exact standard-rating selection, Equal Load Sharing/N-1 capacity basis, and explicit draft yard-band installation assessment with unsupported-band review; 13 Phase 5 tests.
- Phase 6: `DONE` — deterministic BOQ baseline and release-template adapters, allow-listed quantity rules, F/V/O/PS/EXCL handling, COMPOSITE/BREAKDOWN mutual exclusion, delta-based manual edits, and duplicate-scope detection; five Phase 6 tests.
- Phase 7: `DONE` — Decimal Low/Base/High costing, sequential waterfall, HALF_UP money rounding, SINGLE_POINT_PRICE fallback, missing-Base review handling, and seven reconciliation/rounding tests.
- Phase 8: `DONE` — `app.py`/`st.navigation`, workflow pages, single-aggregate `WorkspaceState`, coordinator orchestration, validation, warning/override rendering, STALE invalidation, and seven Streamlit/coordinator tests.
- Phase 9: `DONE` — canonical immutable project package JSON with schema/data versions, reference hashes, warnings, overrides, and reconciliation; UTF-8 BOM CSV export/import for BOQ, cost, and reference datasets; and an exactly eight-sheet Excel export with reconciliation formulas and Thai-text support. Phase 9 has six export/round-trip tests.
- Phase 10: `DONE` — full workflow golden integration, Hypothesis property invariants, release data-contract closure, CSV formula-safety, packaging contract, Linux-compatible smoke coverage, CI quality gates, wheel-build job, and dependency/static security jobs. Phase 10 has six verification/smoke tests.
- Phase 11: `DONE` — bilingual UX, accessibility-oriented labels/help, disclaimer, README, deployment guide, Community Cloud procedure, AppTest contracts, live desktop/tablet smoke evidence, restricted-access and rollback procedures, and release checklist.

## Phase 4 implementation record

Changed or added:

- `src/solar_design/models/catalogue.py` — preserves nullable cable manufacturer fields and OD/temperature data, validates explicit model CSA labels against structured CSA, and permits a missing PE target to remain unassessed.
- `src/solar_design/calculations/wiring/catalogue.py` — pure adapters for cable, ampacity-to-cable identity, PE mapping, and conduit records from a pinned `ReferenceSnapshot`; certified conduit ID is preferred and screening ID remains flagged.
- `src/solar_design/calculations/wiring/engine.py` — exact PE lookup without S/2 extrapolation, `MISSING`/`REVIEW` results for absent PE/OD, broken `#REF!` and blank rows, model/CSA hard blocking, and integer cable-piece backtracking for parallel conduits.
- `src/solar_design/calculations/wiring/__init__.py`
- `src/solar_design/calculations/__init__.py`
- `tests/phase4/test_wiring.py` — release adapter, exact PE, missing PE, model/CSA mismatch, `#REF!`, blank-row, and parallel-allocation regressions.

Phase 4 behavior is intentionally conservative: missing cable OD never becomes zero, missing PE never becomes a calculated value, and a conduit assignment contains whole physical cable indices only. Cable model CSA is checked when the model explicitly states a CSA; conflicting or mismatched explicit labels are hard validation errors. The release's incomplete AC cable material/insulation fields are preserved as unknown and are not invented by the adapter.

## Phase 5 implementation record

Changed or added:

- `src/solar_design/models/catalogue.py` — transformer product fields may remain nullable when the release supplies standard ratings without HV/LV/product details.
- `src/solar_design/models/results.py` — adds typed `InstallationAssessment` details while preserving the existing `TransformerSelection` interface.
- `src/solar_design/calculations/transformer/catalogue.py` — pure adapters for incomplete transformer rows and exact standard-rating sets from a pinned snapshot; no installation eligibility is inferred from free text.
- `src/solar_design/calculations/transformer/engine.py` — Decimal load/PV sizing, three-phase HV/LV current, smallest supplied standard rating, Equal Load Sharing and N-1 capacity basis, and exact YARD-001..YARD-006 draft-band assessment.
- `src/solar_design/calculations/transformer/__init__.py`
- `src/solar_design/calculations/__init__.py`
- `tests/phase5/test_transformer.py` — 500 kVA current checks, sizing formulas, rating boundaries, 3,001 kVA out-of-range, Equal/N-1, unsupported yard/type bands, release adapters, and single-phase no-guess behavior.

Phase 5 does not create a PEA rule. The six yard bands are preserved as project-guidance `DRAFT` records with `SRC-TRF-001` traceability. A supported band returns a budgetary `PASS` plus Draft/utility-approval findings; unsupported rating/count/type combinations remain `NOT_ASSESSED` and are never interpolated. Single-phase transformer current is blocked because the source set does not supply an approved formula.

## Phase 6 implementation record

Changed or added:

- `src/solar_design/boq/models.py` — validates mutually exclusive composite/breakdown price sources, prevents simultaneous provisional/override prices, keeps `EXCL` out of totals, and includes `PS` only when a provisional price exists.
- `src/solar_design/boq/catalogue.py` — pure adapter from validated release BOQ rows to typed templates; only the explicit `ALWAYS` condition is accepted and no condition text is executed.
- `src/solar_design/boq/generator.py` — exposes deterministic `generate_boq_baseline`, keeps quantity rules on an explicit allow-list, normalizes rule results to Decimal, and reapplies deltas through the existing revision path.
- `src/solar_design/boq/__init__.py`
- `tests/phase6/test_boq.py` — baseline determinism, quantity rules, regeneration/manual edits, idempotent deltas, F/V/O/PS/EXCL, composite/breakdown, duplicate groups, included-scope overlap, and release-template regressions.

Phase 6 does not calculate cost totals or apply the Phase 7 waterfall. `COMPOSITE` uses one composite price, while `BREAKDOWN` uses material/labor/equipment components; both payloads cannot coexist. Duplicate-scope findings are warnings for active, priced lines, while `EXCL` and unpriced `PS` lines are not treated as active total scope.

## Phase 7 implementation record

Changed or added:

- `src/solar_design/costing/models.py` — permits an explicitly missing Base price in a rate record, keeps Low/Base/High scenario types Decimal-first, and reuses Base only when a requested Low/High value is absent.
- `src/solar_design/costing/engine.py` — calculates rounded per-line amounts and the sequential Direct → Preliminaries → OH&P → Contingency → VAT waterfall; missing Base prices are omitted with a `MISSING_BASE_PRICE` `REVIEW` finding, Low/High fallback emits `SINGLE_POINT_PRICE`, and pricing-mode mismatches are blockers.
- `tests/phase7/test_costing.py` — covers the 100,000 THB → 129,764.25 THB example, distinct Low/Base/High totals, per-scenario reconciliation, SINGLE_POINT_PRICE fallback, missing Base, Decimal HALF_UP rounding, BREAKDOWN component totals, and mode mismatch blocking.

Phase 7 consumes immutable Phase 6 `BOQRevision` lines and does not modify the BOQ generator or start the Streamlit/UI work. A missing Base price is never treated as zero silently: the line is excluded from cost totals and requires review. Missing Low/High values reuse a present Base price and are traceable through `SINGLE_POINT_PRICE` warnings.

## Phase 8 implementation record

Changed or added:

- `app.py` — configures the Streamlit entrypoint and explicit `st.navigation` page groups for the workflow.
- `pages/dashboard.py`, `pages/project_inputs.py`, `pages/inverter_selection.py`, `pages/protection_ampacity.py`, `pages/cable_wiring.py`, `pages/transformer_installation.py`, `pages/boq_editor.py`, `pages/cost_summary.py` — presentation-only pages that collect inputs, call the coordinator, display typed results, warnings, review findings, override reasons, and STALE status; no engineering formulas, catalogue lookup, or cost waterfall is embedded in these modules.
- `src/solar_design/ui/state.py` and `src/solar_design/ui/coordinator.py` — immutable `WorkspaceState` plus the input/state coordinator that validates user inputs, preserves findings and override reasons, and invalidates downstream stages after input changes.
- `src/solar_design/services/workflow.py` and `src/solar_design/services/__init__.py` — application-layer workflow orchestration and reference snapshot/rate adapters; the coordinator delegates here so page modules contain no catalogue lookup or engineering formula.
- `src/solar_design/ui/runtime.py` and `src/solar_design/ui/rendering.py` — single session-state adapter and shared warning/status presentation helpers.
- `tests/phase8/test_ui.py` — coordinator end-to-end flow, STALE transition, override validation, navigation, all-page rendering, and Streamlit AppTest coverage.

Phase 8 is integration only. The page modules do not calculate engineering values or implement catalogue/rate lookup; those responsibilities remain in the coordinator and existing pure engines.

## Phase 9 implementation record

Changed or added:

- `src/solar_design/exports/project_json.py` — freezes nested package values at construction, pins `data_version` to the immutable reference snapshot, records manifest file hashes and a canonical snapshot hash, aggregates warnings/overrides, derives Decimal-safe reconciliation records, validates hashes and reconciliation on import, and exposes an expanded JSON schema.
- `src/solar_design/exports/csv_export.py` — stable BOQ/cost CSV column contracts, UTF-8 BOM Thai-safe export/import, formula-injection-safe text handling, strict row/header validation, reference-dataset export, and exact schema/data-version checks for reference CSV import.
- `src/solar_design/exports/excel_export.py` — eight-sheet workbook export from a materialized immutable package payload, visible schema/data/hash/audit/reconciliation rows, Thai text preservation, and BOQ/Cost Summary reconciliation formulas.
- `src/solar_design/exports/__init__.py` — exports the Phase 9 public JSON/CSV/Excel APIs and column contracts.
- `src/solar_design/services/delivery.py` — generates BOQ and cost CSVs from the same frozen `ProjectPackage` used for JSON and Excel.
- `tests/phase9/test_exports.py` — JSON round-trip and tamper detection, nested immutability, exact eight-sheet/formula checks, Thai text, BOQ/cost CSV round-trips, reference CSV version checks, and reconciliation coverage.

Phase 9 exports are built from a `ProjectPackage` that snapshots the pinned `ReferenceSnapshot`; nested mappings are frozen and manifest hashes are checked. JSON import rejects schema/data/hash/reconciliation mismatches. CSV import never evaluates cell formulas and removes only the exporter's own spreadsheet-safety prefix. Excel remains exactly eight sheets: Project Information, Design Calculation, BOQ, Cost Summary, Unit Rates, Transformer Prices, Assumptions, and Sources. PDF generation was intentionally not started.

## Phase 10 implementation record

Changed or added:

- `src/solar_design/services/workflow.py` — corrected the verified integration defect where BOQ release rows use `record_id` rate links (`RATE-*`) while the workflow rate snapshot exposed only `item_code`; both explicit release identifiers are now deterministic aliases, with duplicate alias detection.
- `tests/phase1/test_data_contracts.py` — corrected test-only typing defects exposed by the full Mypy gate; no data model or engineering rule changed.
- `tests/phase10/test_verification.py` — golden default workflow and export determinism, Decimal costing property invariants, release version/hash/source closure, CSV formula-safety, and packaging metadata checks.
- `tests/phase10/test_linux_smoke.py` — non-UI full workflow smoke test intended for Ubuntu CI.
- `pyproject.toml` — adds build, Bandit, and pip-audit to development verification dependencies.
- `.github/workflows/ci.yml` — expands CI to pages, full Mypy/compile/pip-check, coverage gate, wheel build/install, pip-audit, Bandit, and an Ubuntu Linux smoke job.

Phase 10 changed only a data-identifier integration defect proven by the golden test. No engineering calculation, catalogue rule, utility rule, or source value was changed. The full workflow now reaches the seeded BOQ rate through either release identifier and the default golden Base total is `8,560.00 THB`.

## Phase 11 implementation record

Changed or added:

- `app.py` — keeps the Community Cloud root entrypoint importable for the `src` package layout, adds bilingual navigation labels, shared Help guidance, and the bilingual preliminary-use disclaimer.
- `pages/*.py` — adds Thai/English page headings, descriptions, labels, action text, help text, status/finding text, and responsive table labels; replaces deprecated `use_container_width` calls with `width="stretch"`. The pages still delegate all engineering work to the existing coordinator and services.
- `src/solar_design/ui/rendering.py` — adds shared bilingual disclaimer/help and accessible text-first warning/status primitives; no calculation logic was added.
- `README.md` — replaces the original planning prompt with the operational user guide, safety boundary, local run commands, quality gates, workflow boundary, and release links.
- `docs/DEPLOYMENT.md` — documents Community Cloud deployment, private/restricted access acceptance, secrets handling, desktop/tablet smoke checks, and Git-based rollback.
- `docs/RELEASE_CHECKLIST.md` — release owner, data/security, automated QA, UX/accessibility, manual smoke, restricted access, deployment, rollback, and sign-off checklist.
- `tests/phase11/test_release.py` — release-document/security contracts and Streamlit AppTest checks for bilingual notice, page titles, and descriptive actions.
- `tests/phase8/test_ui.py` — updates the existing AppTest selector for the bilingual Save Project Inputs action.

Phase 11 did not change formulas, catalogue values, source data, PE lookup behavior, conduit limits, transformer rules, BOQ rules, or cost rules. Restricted-access and rollback behavior is documented and contract-tested; a live Community Cloud access test requires an owner-provided deployed URL and authorized test identities and was not performed from this local workspace.

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
- `python -m pytest -p no:cacheprovider -q` — `34 passed` after Phase 4.
- Phase 4 scoped checks: `python -m ruff check src/solar_design/models src/solar_design/calculations/wiring tests/phase4` — passed.
- Phase 4 scoped checks: `python -m mypy src/solar_design/models src/solar_design/calculations/wiring tests/phase4` — passed.
- `python -m pytest -p no:cacheprovider -q` — `47 passed` after Phase 5.
- Phase 5 scoped checks: `python -m ruff check src/solar_design/models src/solar_design/calculations/transformer tests/phase5` — passed.
- Phase 5 scoped checks: `python -m mypy src/solar_design/models src/solar_design/calculations/transformer tests/phase5` — passed.
- `python -m compileall -q src tests` — passed after Phase 5.
- `python -m pytest -p no:cacheprovider -q` — `52 passed` after Phase 6.
- Phase 6 scoped checks: `python -m ruff check src/solar_design/boq tests/phase6` — passed.
- Phase 6 scoped checks: `python -m mypy src/solar_design/boq tests/phase6` — passed.
- `python -m pytest -p no:cacheprovider -q` — `59 passed` after Phase 7.
- Phase 7 scoped checks: `python -m ruff check src/solar_design/costing tests/phase7` — passed.
- Phase 7 scoped checks: `python -m mypy src/solar_design/costing tests/phase7` — passed.
- `python -m ruff check src tests` — passed after Phase 7.
- `python -m compileall -q src tests` — passed after Phase 7.
- `python -m pytest -p no:cacheprovider -q` — `66 passed` after Phase 8.
- Phase 8 scoped checks: `python -m ruff check app.py pages src/solar_design/ui` — passed.
- Phase 8 scoped checks: `python -m mypy src/solar_design/ui` — passed.
- Phase 8 scoped checks: `python -m compileall -q app.py pages src/solar_design/ui` — passed.
- Phase 8 AppTest/coordinator tests: `7 passed`; navigation and all eight Phase 8 pages rendered without exceptions.
- `python -m pytest -p no:cacheprovider -q` — `72 passed` after Phase 9. Streamlit AppTest process cleanup still emits a Windows sandbox `PermissionError` traceback after a successful exit; it does not fail the test run.
- `python -m pytest -p no:cacheprovider --cov=solar_design --cov-report=term-missing --cov-fail-under=75 -q` — `82 passed`, total coverage `84.56%` after Phase 11.
- Phase 10 scoped checks: `python -m pytest -p no:cacheprovider -q tests/phase10` — `6 passed`.
- Full Mypy: `python -m mypy src tests` — passed for 76 files after Phase 11.
- Full Ruff: `python -m ruff check src tests app.py pages` — passed after Phase 11.
- Full compile: `python -m compileall -q src tests app.py pages` — passed after Phase 11.
- Dependency consistency: `python -m pip check` — passed.
- CI now defines separate Ubuntu package, security, and Linux-smoke jobs; GitHub execution was not available from this local workspace.
- Phase 9 scoped checks: `python -m ruff check src/solar_design/exports tests/phase9` — passed.
- Phase 9 scoped checks: `python -m mypy src/solar_design/exports tests/phase9` — passed.
- Phase 9 scoped checks: `python -m compileall -q src/solar_design/exports tests/phase9` — passed.
- Full Ruff: `python -m ruff check src tests app.py pages` — passed after Phase 9.
- Full compile: `python -m compileall -q src tests app.py pages` — passed after Phase 9.
- `git diff --check` — passed; Git reported only existing line-ending normalization warnings.
- Phase 11 scoped AppTest and release contracts: `python -m pytest -p no:cacheprovider tests/phase8 tests/phase11 -q` — `11 passed`.
- Phase 11 scoped Ruff: `python -m ruff check src tests app.py pages` — passed after bilingual UI/docs changes.
- Phase 11 scoped Mypy: `python -m mypy src tests` — passed for 76 source files.
- Live local desktop smoke: landing page, workflow run, all eight navigation pages, bilingual labels/help/disclaimer, current results, warnings, and Cost Summary — passed.
- Live local tablet smoke at `1024x768`: all eight pages, no unhandled exception, 75 focusable controls, and no document-level horizontal overflow — passed.
- Live keyboard focus sample: Help, Deploy, Main menu, disclaimer, heading link, and table control were reachable by Tab — passed.
- Restricted-access and rollback procedure: documentation and release-contract tests passed; live Community Cloud access denial/rollback was not run without an owner-provided deployed URL and authorized test identities.

## Known limitations and next action

- No engineering record is promoted to `VERIFIED`; owner approvals, utility requirements, and source licensing remain open.
- The data release is not approved for construction issue and is not a substitute for current manufacturer, standards, or utility documents.
- Phase 9 export/reporting is complete for JSON, Excel, and CSV; PDF generation remains intentionally out of scope.
- Protection remains assessment-only: all current breaker catalogue rows are `DRAFT`/`NOT_ASSESSED`, and no breaker is automatically selected until fault level, interrupting duty, terminal temperature, coordination, and utility rules are approved.
- Ampacity table rows and grouping factors remain `DRAFT` or `ASSUMPTION`; a mathematical PASS is not construction approval.
- Local `pip-audit`/Bandit executables were not installed in this Windows environment; the CSV formula-safety test passed and CI now installs/runs both tools in the security job.
- Local wheel build was attempted but blocked by the managed Windows environment's pip temporary build-tracker permission (`WinError 5`); the Ubuntu package job performs the build and wheel-install smoke check.
- The current data release does not source nominal AC voltage, phase configuration, or maximum AC current for the inverter rows; therefore AC current can remain unassessed from the release snapshot and must not be guessed.
- The current cable release contains broken PV OD references and incomplete AC cable material/insulation/temperature fields; the implementation returns missing/review or requires explicit caller filters rather than guessing.
- PE mappings are still Draft and exact-only; absent sizes remain `MISSING`/`REVIEW` and are not an adiabatic or arithmetic fallback.
- Conduit dimensions are screening-only until certified internal diameters are supplied; a mathematical fill pass is not construction approval.
- Transformer product rows remain generic Draft rating options; HV/LV/product details must be supplied before product-level current or installation approval.
- Yard dimensions are budgetary Draft guidance only; PEA/utility eligibility, pole/platform rules, grounding topology, impedance, losses, and oversize thresholds remain open.
- BOQ template rows and rates remain Draft; Phase 7 applies explicit missing-Base review handling and Base fallback for missing Low/High, but it does not promote Draft rates to approved commercial prices.
- Duplicate-scope findings require engineering/commercial review and do not by themselves compute or approve a cost total.
- The UI is a budgetary workflow shell: engineering and commercial records retain Draft/Unknown/Requires-approval findings, and no construction approval is implied.
- Phase 11 is complete for local UX/accessibility smoke and release documentation. A live Community Cloud restricted-access and rollback rehearsal remains an owner-operated deployment step because this workspace has no deployed URL or authorized test identities.
- Streamlit AppTest cleanup on this managed Windows environment may emit a post-success temporary-folder `PermissionError` traceback; the test process still exits 0 and no app exception is reported.

Before committing, stage only the approved Phase 4 through Phase 11 files and the existing Phase 1 through Phase 3 implementation files that belong to this worktree. Preserve pre-existing `desktop.ini`, and review any unrelated files before staging.
