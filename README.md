/plan

You are the Lead Software Architect, Senior Electrical Engineer,
and Cost Estimation System Designer for this project.

Goal:
Plan a production-quality Streamlit application for electrical system
design and budgetary cost estimation in Thailand.

IMPORTANT:
DO NOT implement the application yet.
DO NOT start writing Streamlit pages yet.
First inspect all project files and engineering references thoroughly,
then produce the implementation architecture and phased development plan.

==================================================
SOURCE OF TRUTH
==================================================

Inspect ALL files under the supplied project/reference folders.

The engineering scope consists of 4 linked design engines:

1. Inverter Selection
2. Cable Ampacity / Maximum 70°C Design Check
3. AC Cable + Ground Cable + Conduit Selection
4. Transformer Selection + Installation Type + BOQ/Cost Estimate

Do not treat these as four independent calculators.

They must form one engineering workflow:

Project Inputs
    ↓
PV / Load Design
    ↓
Inverter Selection
    ↓
AC Current Calculation
    ↓
Protection Device / CB
    ↓
Cable Ampacity Check
    ↓
Cable Selection
    ↓
Grounding Conductor Selection
    ↓
Conduit / Raceway Selection
    ↓
Transformer Requirement
    ↓
Transformer Sizing
    ↓
Transformer Installation Design
    ↓
Automatic BOQ
    ↓
Cost Estimate
    ↓
Engineering Summary / Export

==================================================
ARCHITECTURE REQUIREMENT
==================================================

The Streamlit UI MUST NOT contain the core engineering formulas.

Separate the project into at least:

- ui/
- domain/
- calculations/
- rules/
- boq/
- costing/
- data/
- models/
- services/
- exports/
- tests/
- assets/

Engineering calculations must be pure/testable Python functions wherever possible.

Rules and reference values that may change must be data-driven
(CSV / JSON / YAML as appropriate), not scattered hard-coded values
inside Streamlit page files.

==================================================
ENGINEERING TRACEABILITY
==================================================

For every design rule determine whether it is:

- Verified
- Draft
- Assumption
- Manufacturer data
- Utility requirement
- Requires utility approval
- User override
- Unknown

Every calculated recommendation should ultimately be able to expose:

- input
- formula/rule used
- calculated value
- selected value
- source/reference
- verification status
- warning
- override reason

Do not silently convert uncertain engineering information into a fixed rule.

==================================================
TASK FOR THIS /plan
==================================================

Inspect the available files and produce:

1. Current source inventory
2. Engineering requirements extracted from source 1–4
3. Missing or conflicting information
4. Proposed application architecture
5. Proposed Python package/file structure
6. Data schema for:
   - inverter database
   - cable database
   - breaker/protection database
   - conduit database
   - engineering design rules
   - transformer database
   - transformer prices
   - unit rates
   - BOQ templates
   - source/reference registry

7. Calculation dependency graph
8. Streamlit page/navigation structure
9. Session-state/project model
10. Engineering audit-trail design
11. BOQ generation architecture
12. Cost calculation architecture
13. Excel/project export architecture
14. Unit-test strategy
15. Streamlit AppTest strategy
16. Validation and warning strategy
17. Proposed development phases
18. Acceptance criteria for every phase
19. Major technical and engineering risks
20. Decisions/questions that need owner confirmation

==================================================
DEVELOPMENT PHASES
==================================================

Create a plan that preferably separates work into:

Phase 0 - Repository audit and normalization
Phase 1 - Domain/data models
Phase 2 - Inverter design engine
Phase 3 - Cable ampacity engine
Phase 4 - Cable/Ground/Conduit engine
Phase 5 - Transformer design engine
Phase 6 - BOQ generation engine
Phase 7 - Cost estimation engine
Phase 8 - Streamlit UI integration
Phase 9 - Export/reporting
Phase 10 - Verification/testing
Phase 11 - UI/UX refinement

For every phase specify:

- objective
- files to create/change
- dependencies
- engineering rules involved
- tests required
- definition of done

==================================================
SUB-AGENT DECISION
==================================================

Before using sub-agents, determine whether delegation would materially
improve the plan.

If sub-agents are available, they may be used ONLY for parallel READ-ONLY
analysis of independent domains such as:

A. Inverter rules
B. Cable/ampacity/ground/conduit rules
C. Transformer/installation/BOQ rules
D. Existing software/data architecture

Sub-agents must NOT modify production files during this planning stage.

The lead agent remains responsible for reconciling conflicts and producing
one coherent master architecture.

==================================================
OUTPUT
==================================================

Create or update:

docs/IMPLEMENTATION_PLAN.md
docs/ENGINEERING_RULE_MATRIX.md
docs/DATA_MODEL.md

Do not implement production code until I approve the plan.

At the end return:

1. Recommended architecture
2. Development phase summary
3. Proposed sub-agent breakdown
4. Major unresolved engineering questions
5. Exact recommended next Codex command