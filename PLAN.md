# แผนพัฒนา Solar Electrical Design & Cost Estimation Streamlit Application

## 1. สรุปผลตรวจสอบและขอบเขต

Repository ยังอยู่ระดับเอกสารอ้างอิง ยังไม่มี Python application, tests, dependency manifest หรือ CI

### Source inventory

- เอกสารอ้างอิง 18 ไฟล์: Inverter 2, Cable 70°C 5, Cable/Ground/Conduit 5, Transformer/BOQ 6
- ZIP เป็น snapshot ที่ตรงกับไฟล์อ้างอิงทั้ง 18 ไฟล์แบบ byte-for-byte
- [README.md](<D:/OneDrive - PTTOR/PTTOR มาตรฐาน/_หนังสือ เกี่ยวกับ EE/__ขั้นตอนการออกแบบ Solar Rooftop-V.1/_1.Guideline Solar Survey/12.Streamlit-Inverter(AC)-Transformer/README.md>) เป็น planning brief
- [Cable_Containme.xlsx](<D:/OneDrive - PTTOR/PTTOR มาตรฐาน/_หนังสือ เกี่ยวกับ EE/__ขั้นตอนการออกแบบ Solar Rooftop-V.1/_1.Guideline Solar Survey/12.Streamlit-Inverter(AC)-Transformer/3.การเลือกสายไฟ-ท่อร้อยสายไฟ (AC-Ground)/Cable_Containme.xlsx>) เป็น prototype สำหรับ conduit fill ไม่ใช่ระบบเลือกสายครบวงจร
- [Transformer specification](<D:/OneDrive - PTTOR/PTTOR มาตรฐาน/_หนังสือ เกี่ยวกับ EE/__ขั้นตอนการออกแบบ Solar Rooftop-V.1/_1.Guideline Solar Survey/12.Streamlit-Inverter(AC)-Transformer/4.การเลือกหม้อแปลง/2.Program ออกแบบการติดตั้งหม้อแปลง-Phase-2.md>) มี requirements, ราคา และ BOQ มากที่สุด แต่หลายรายการยังเป็น Draft

ข้อค้นพบสำคัญ:

- Inverter 5 รุ่นใช้ค่า DC/AC เท่ากับ 1.40 โดยนัย; ห้ามใช้เป็นกฎสากล ส่วน SG350HX-20 ไม่มีค่า kWp ที่ใช้ออกแบบได้
- แนวทาง strict 70°C ให้ required table ampacity `129.10 A` สำหรับโหลด 100 A, สาย 90°C, ambient 40°C
- วิธีเลือกสาย 125% ให้ตัวอย่างประมาณ 72°C จึงขัดกับ strict 70°C
- Conduit fill ใช้ 53% สำหรับสาย 1 เส้น, 31% สำหรับ 2 เส้น และ 40% สำหรับตั้งแต่ 3 เส้น
- Excel มีสูตร 1,373 cells และ `#REF!` 48 cells ที่ `E10:P13`; blank rows บางรายการแสดงผลผิดเป็น PASS และการแบ่งสายหลายท่อใช้พื้นที่แบบเศษส่วนซึ่งอาจให้ผล false pass
- กฎ PE แบบ `S/2` ไม่มีแหล่งอ้างอิงครบและไม่มีข้อมูลต่ำกว่า 35 mm²
- สูตรหม้อแปลงและ yard dimensions ใช้เป็น Draft estimator ได้ แต่ยังไม่มีกฎ PEA ที่กำหนดว่า rating ใดติดตั้งแบบ pole/platform/yard ได้
- ยังไม่มีข้อมูลเพียงพอสำหรับ voltage drop, short-circuit withstand และ protection coordination; รุ่นแรกต้องแสดง `NOT ASSESSED`
- ไม่มีเอกสาร quotation ต้นฉบับหรือขอบเขตราคาครบ จึงถือราคาปัจจุบันเป็น Draft/Single-point

สถานะกฎมาตรฐาน:

`VERIFIED`, `DRAFT`, `ASSUMPTION`, `MANUFACTURER_DATA`, `UTILITY_REQUIREMENT`, `REQUIRES_UTILITY_APPROVAL`, `USER_OVERRIDE`, `UNKNOWN`, `NOT_PERMITTED`

ปัจจุบันยังไม่มีกฎใดควรถูกจัดเป็น `VERIFIED` จนกว่าจะผ่านการอนุมัติของ engineering owner

## 2. สถาปัตยกรรมและ interfaces

ใช้ modular monolith โดย Streamlit เป็น presentation layer เท่านั้น:

```text
Project Inputs / System Basis
        ↓
Inverter Engine
        ↓
AC Circuit + Protection Candidate
        ↓
70°C Ampacity Engine
        ↓
Cable + PE + Discrete Conduit Allocation
        ↓
Transformer Sizing + Installation Assessment
        ↓
Immutable DesignRun
        ↓
BOQ Baseline + User Deltas
        ↓
Low / Base / High Cost Estimate
        ↓
JSON / Excel / CSV + Audit Trail
```

โครงสร้างหลัก:

```text
app.py
src/solar_design/
  ui/
  domain/
  models/
  calculations/
    inverter/
    protection/
    ampacity/
    wiring/
    transformer/
  rules/
  services/
  repositories/
  boq/
  costing/
  audit/
  validation/
  exports/
  schemas/
data/releases/<data_version>/
assets/
tests/{unit,contract,integration,app,golden}/
docs/
.streamlit/config.toml
requirements.txt
pyproject.toml
```

Interfaces สำคัญ:

- `run_design(ProjectRevision, ReferenceSnapshot) -> DesignRun`
- `select_inverters(...) -> InverterSelection`
- `calculate_ac_circuits(...) -> list[CircuitRequirement]`
- `select_protection(...) -> ProtectionSelection`
- `check_70c_ampacity(...) -> AmpacityAssessment`
- `select_cables_and_pe(...) -> WiringSelection`
- `allocate_conduits(...) -> ConduitAllocation` โดยจัดจำนวนสายเป็นจำนวนเต็มต่อท่อ
- `size_transformer(...) -> TransformerSelection`
- `generate_boq(DesignRun, BOQTemplate) -> BOQRevision`
- `calculate_cost(BOQRevision, RateSnapshot, CostPolicy) -> CostRevision`

ทุก engine เป็น pure function และห้าม import Streamlit, filesystem, pandas หรือ session state

### Data schemas

ทุก record มี `record_id`, `revision`, `verification_status`, `source_id`, `effective_from`, `effective_to`, `notes`

| Dataset | Fields เฉพาะ |
|---|---|
| Inverter | manufacturer, model, AC kW/kVA, voltage, phase, PF range, nominal/max current, max DC kWp nullable, MPPT/input limits, ambient reference, derating profile |
| Cable | family, manufacturer, material, insulation, voltage class, cores, loaded conductors, CSA, OD, temperature rating |
| Breaker | manufacturer/model, poles, AT/AF, voltage, breaking capacity, terminal temperature, adjustable settings |
| Conduit | type, trade size, standard, OD, wall thickness, certified ID, internal area, screening flag |
| Design rules | domain, utility profile, applicability, `expression_key`, parameters, outcome, severity, override policy |
| Transformer | manufacturer/model/type, kVA, HV/LV, phases, vector group, impedance, losses, installation eligibility |
| Transformer prices | quotation number/date, transformer key, THB price, VAT flag, delivery/crane/installation/testing/inspection tri-state flags, validity |
| Unit rates | item code, category, TH/EN description, unit, low/base/high nullable, included/excluded scope, source date |
| BOQ templates | installation type, condition key, quantity-rule key, pricing mode, cost status, duplicate-cost group |
| Source registry | title, issuer, edition, page/table, local path/URL, SHA-256, authority, licensing, reviewer and review date |

เพิ่ม datasets สำหรับ ampacity tables, correction factors, standard transformer ratings และ cable OD โดยแยกจากกฎ executable ห้ามประมวลผลสูตรจากข้อความใน CSV; `expression_key` ต้อง map ไปยังฟังก์ชันที่ทดสอบแล้วเท่านั้น

### State และ audit trail

`st.session_state` เก็บ `WorkspaceState` เพียง aggregate เดียว ซึ่งอ้างถึง:

- `ProjectDraft`
- immutable `ProjectRevision`
- immutable `ReferenceSnapshot`
- immutable `DesignRun`
- `BOQRevision`
- `CostRevision`

การแก้ input ต้นทางทำให้ผล downstream เป็น `STALE` ทันที การคำนวณใหม่สร้าง revision ใหม่ ส่วน BOQ edits เก็บเป็น delta เพื่อไม่ให้ regeneration ลบการแก้ของผู้ใช้

ทุกผลคำนวณสร้าง `DecisionRecord` ที่เก็บ input, units, formula/rule version, intermediate values, candidates/rejection reasons, calculated/selected value, source, status, warnings และ override reason

## 3. UI, validation, BOQ, costing และ exports

ใช้ `st.navigation`/`st.Page` ตาม [Streamlit navigation API](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation):

1. Dashboard
2. Project & System Basis
3. PV / Inverter Selection
4. Protection & 70°C Ampacity
5. Cable / PE / Conduit
6. Transformer & Installation
7. BOQ Editor
8. Cost Summary
9. Assumptions & Audit
10. Master Data
11. Export

นโยบายที่ล็อกแล้ว:

- PEA-first; MEA/Other แสดง unsupported warning
- Strict 70°C เป็นค่าเริ่มต้น
- Draft/Unknown/Requires approval แสดง warning แต่ไม่หยุด budget calculation หรือ export
- หากผู้ใช้เปลี่ยน recommendation เป็นค่าอื่น ต้องบันทึก `USER_OVERRIDE` และเหตุผล
- Voltage drop, fault withstand และ coordination แสดง `NOT ASSESSED` ใน UI/exports
- หม้อแปลง 2 ลูกเลือกระหว่าง Equal Load Sharing และ N-1; ค่าเริ่มต้นเป็น Equal Sharing
- Hard blockers ยังคงใช้กับข้อมูลผิด schema, ค่าติดลบ, PF/derating ผิดช่วง, สูตรเสีย, model/CSA mismatch และข้อมูลบังคับที่ขาด
- ทุกหน้าผลลัพธ์และ export แสดงข้อความ Budgetary Estimate ตามเอกสารต้นทาง

BOQ:

- Baseline สร้างจาก DesignRun เท่านั้น
- `pricing_mode=COMPOSITE` ใช้ Unit Price หรือ `BREAKDOWN` ใช้ Material+Labor+Equipment อย่างใดอย่างหนึ่ง ป้องกัน double count
- `EXCL` ไม่รวมยอด; `PS` รวมเมื่อมี provisional value
- ตรวจ duplicate scope เช่น crane, transport, cable ที่รวมกับ ground rod
- Regeneration ต้อง idempotent และรักษา user deltas

Cost waterfall:

```text
Direct Cost
Preliminaries = Direct Cost × rate
OH&P = (Direct Cost + Preliminaries) × rate
Contingency = (Direct Cost + Preliminaries + OH&P) × rate
Subtotal before VAT = ผลรวมข้างต้น
VAT = Subtotal × VAT rate
Grand Total = Subtotal + VAT
```

ใช้ `Decimal` และปัดเศษ 0.01 บาทในแต่ละ BOQ line และแต่ละ cost layer หาก Low/High ไม่มี ให้ reuse Base พร้อม `SINGLE_POINT_PRICE` warning

Exports:

- JSON เป็น canonical project package พร้อม schema/data version, hashes, warnings, overrides และ revisions
- Excel 8 sheets: Project Information, Design Calculation, BOQ, Cost Summary, Unit Rates, Transformer Prices, Assumptions, Sources
- Excel formulasใช้เพื่อ audit/reconciliation เท่านั้น; Python results เป็นค่าหลัก
- CSV สำหรับ BOQ และ master data
- PDF เลื่อนไปหลัง v1
- Project/master uploads ต้องตรวจ extension, MIME, size, schema และปฏิเสธ unknown fields ที่อันตราย

Deployment:

- GitHub เป็น source of truth และ deploy เป็น private/restricted Streamlit Community Cloud app
- ไม่มี database; ข้อมูลอยู่ใน session และบันทึกผ่าน JSON/CSV downloads
- การแก้ master data ถาวรทำผ่าน GitHub เท่านั้น
- ต้องตั้ง repository/app visibility และ viewer list ตาม [Community Cloud private sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- วาง entrypoint, configuration และ dependency file ตาม [Community Cloud file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)

## 4. Phased implementation และ acceptance criteria

| Phase | Objective / files | Dependencies และ rules | Tests | Definition of done |
|---|---|---|---|---|
| 0 — Audit | สร้าง `docs/IMPLEMENTATION_PLAN.md`, `ENGINEERING_RULE_MATRIX.md`, `DATA_MODEL.md`; inventory, hashes, conflict log | ไม่มี; ยังไม่สร้าง production code | ตรวจไฟล์ครบ 21 รายการ, ZIP duplicate, rule/source links | Engineering owner เห็นทุก Draft/Unknown และคำถามที่ต้องอนุมัติ |
| 1 — Models/data | สร้าง package, Pydantic models, enums, units, schemas, versioned data release | Phase 0; status and source policy | Schema, uniqueness, referential-integrity, round-trip tests | Sample records ทุก dataset validate และไม่มี orphan source |
| 2 — Inverter | สร้าง inverter catalogue/engine และ circuit outputs | Phase 1; 1.40 เป็น model-specific assumption; SG350 kWp unknown | Model eligibility, exact ratio, missing limits, manual override | คืนผล typed พร้อม trace; ไม่สร้าง kWp สำหรับ SG350 โดยไม่มีข้อมูล |
| 3 — Protection/ampacity | สร้าง breaker interface, grouping factors และ strict 70°C engine | Phase 1–2; breaker catalogue ยัง Draft | 100 A→129.10 A; 25 mm² fail/35 mm² pass; grouping boundaries | ทุกผลระบุ table, conditions, factor chain และ warning |
| 4 — Cable/PE/conduit | สร้าง cable selection, PE lookup และ integer conduit allocation | Phase 3; S/2 Draft; fill 53/31/40 | Regression สำหรับ `#REF!`, blank rows, model/CSA mismatch, parallel allocation | ไม่มี false PASS; missing OD/PE คืน MISSING ไม่ใช่ค่าเดา |
| 5 — Transformer | สร้าง load/PV sizing, standard rating, HV/LV current, duty modes, installation assessment | Phase 1–4; PEA-first, yard rules Draft | 500 kVA currents, size boundaries, above 3,000, Equal/N-1, unsupported bands | ผล sizing ทำซ้ำได้และ installation status โปร่งใส |
| 6 — BOQ | สร้าง template evaluator, baseline/delta และ duplicate-cost detection | Design outputs จาก Phase 2–5 | Determinism, idempotence, quantity rules, EXCL/PS, duplicate crane/cable | Regenerate แล้ว manual edits ไม่สูญหาย |
| 7 — Costing | สร้าง Low/Base/High และ sequential waterfall | Phase 6; single-point fallback | Direct 100,000 + 5/10/5% + VAT 7% = 129,764.25; rounding and missing price | ยอด reconcile ทุก scenario และ warning ครบ |
| 8 — Streamlit UI | สร้าง `app.py`, UI pages, session coordinator, theme และ normalized assets | Engines และ services พร้อม | Streamlit AppTest navigation, validation, rerun, stale state, warning/override | Workflow ตั้งแต่ project ถึง cost ใช้งานได้โดยไม่มีสูตรใน UI |
| 9 — Export | JSON/Excel/CSV services | Stable revisions จาก Phase 8 | JSON schema/round-trip, Excel sheets/formulas/reconciliation, Thai text | โหลด project กลับได้และ export สร้างจาก snapshot เดิม |
| 10 — Verification | เพิ่ม integration/golden/property tests, CI, dependency/security checks | Phase 1–9 | Full workflow, data contracts, coverage, Linux smoke test | Test suite ผ่าน, ไม่มี unresolved software blocker, deployment build ผ่าน |
| 11 — UX/release | ปรับ Thai/English UX, accessibility, help text, README และ deployment guide | Phase 10 | AppTest ตาม [official multipage testing workflow](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest), tablet/manual smoke test | Private Community Cloud pilot พร้อม versioned release และ rollback instructions |

## 5. ความเสี่ยง สมมติฐาน และงานที่ต้องยืนยัน

ความเสี่ยงหลัก:

- เอกสารมาตรฐานมีเพียงบางหน้าและผสม Thai, BS และ AS/NZS โดยยังไม่มี hierarchy/edition ที่อนุมัติ
- อาจมีข้อจำกัดลิขสิทธิ์ในการแจกจ่ายตารางมาตรฐานผ่าน repository/app
- ไม่มี PEA installation eligibility, approved drawings, protection/metering และ grounding criteria
- ราคาไม่มี quotation scope, validity และ Low/High จริง
- Warning-only policy อาจถูกเข้าใจเป็นการรับรอง จึงต้องแสดงสถานะและ disclaimer ในทุก export
- Community Cloud ไม่มี persistence ตามสถาปัตยกรรมนี้; session loss ต้องกู้ผ่าน JSON
- หาก repository เป็น public เอกสารอ้างอิงและราคาใน GitHub ยังคง public แม้ตัวแอปตั้ง private

คำถามวิศวกรรมที่ owner ต้องยืนยันใน Phase 0:

- ฉบับและลำดับความสำคัญของมาตรฐานที่ใช้
- PEA rules สำหรับ pole/platform/yard, voltage class และ maximum transformer rating
- Breaker AT/AF, breaking capacity, fault level และ coordination policy
- Inverter datasheets และ maximum output current/DC limits
- แหล่งและขอบเขตของ PE `S/2`
- Voltage-drop limit, short-circuit data และ cable installation methods
- Ground resistance target, soil resistivity, electrode topology สำหรับ 2 transformers
- Transformer impedance, losses, reverse-power/step-up และ oversize threshold
- Quotation documents, included/excluded scopes, validity และ actual Low/High rates
- สิทธิ์ในการเก็บหรือเผยแพร่ภาพ/ตารางอ้างอิง

Sub-agent breakdown ที่ใช้สำหรับ audit และแนะนำให้ใช้ต่อใน Phase 0:

- A: Inverter rules/datasheets
- B: Ampacity, cable, PE และ conduit
- C: Transformer, installation, grounding, BOQ และ costing
- D: Architecture, data governance, testing และ deployment
- Lead agent เป็นผู้รวมสถานะกฎ แก้ conflicts และอนุมัติ master plan

Exact recommended next Codex command:

```text
/work ดำเนินการ Phase 0 เท่านั้นตามแผนที่อนุมัติ: สร้าง docs/IMPLEMENTATION_PLAN.md, docs/ENGINEERING_RULE_MATRIX.md และ docs/DATA_MODEL.md จากผล audit ทั้งหมด โดยยังไม่สร้าง production code; ตรวจ inventory, source hashes, rule statuses, conflicts และ owner-confirmation checklist ให้ครบ จากนั้นสร้าง branch phase-0-planning-docs, commit และ push ไป GitHub
```
