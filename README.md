# Solar Electrical Design (Thailand)

Streamlit workflow สำหรับการออกแบบระบบไฟฟ้า AC ของ Solar Rooftop และการประเมิน
งบประมาณหม้อแปลงแบบตรวจสอบย้อนกลับได้ รองรับ UX ภาษาไทย/อังกฤษในทุกหน้าหลัก

This repository contains a traceable Streamlit workflow for solar AC electrical
design and budgetary transformer installation assessment. The user interface is
bilingual (Thai/English); engineering calculations and reference-data lookups
remain in the typed service and calculation layers.

## Safety boundary | ขอบเขตการใช้งาน

ผลลัพธ์เป็นการประเมินเบื้องต้นด้านวิศวกรรมและงบประมาณเท่านั้น ไม่ใช่แบบก่อสร้าง
หรือคำสั่งจัดซื้อ ต้องยืนยันข้อมูลหน้างาน ข้อมูลผู้ผลิต ข้อกำหนดการไฟฟ้า
การประสานการป้องกัน และแบบฉบับสุดท้ายกับวิศวกรผู้รับผิดชอบก่อนใช้งานจริง

The application is preliminary engineering and budgetary assessment only. Confirm
site data, manufacturer information, utility requirements, protection coordination,
and the final design with the responsible engineer before procurement or construction.

## Run locally | การรันในเครื่อง

Requires Python 3.11–3.14.

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
python -m streamlit run app.py
```

Open the displayed local URL, start at **Project Inputs | ข้อมูลโครงการ**, save the
basis, run the workflow, then review warnings and STALE status on every downstream page.

## Workflow | ลำดับงาน

Project Inputs → PV/Inverter → Protection/Ampacity → Cable/PE/Conduit →
Transformer/Installation → BOQ → Cost Summary

The pages only collect inputs and present typed results. Do not add engineering
formulas, catalogue lookup, or cost-waterfall logic to `app.py` or `pages/`.

## Quality gates | การตรวจสอบคุณภาพ

```text
python -m pytest -p no:cacheprovider --cov=solar_design --cov-report=term-missing --cov-fail-under=75 -q
python -m ruff check src tests app.py pages
python -m mypy src tests
python -m compileall -q src tests app.py pages
python -m pip check
```

The release is blocked when tests fail, warnings/overrides disappear, immutable
export reconciliation changes, or a defect would require changing an engineering
rule without owner approval.

## Release and deployment | การปล่อยรุ่นและนำขึ้นระบบ

- [Deployment guide and Community Cloud procedure](docs/DEPLOYMENT.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Current handoff](docs/CODEX_HANDOFF.md)
- [Engineering rule matrix](docs/ENGINEERING_RULE_MATRIX.md)
- [Data model](docs/DATA_MODEL.md)

The Community Cloud entrypoint is `app.py`; the pinned reference release is under
`data/releases/2026.08-draft`. Keep `.streamlit/secrets.toml` out of Git and use
Community Cloud App settings for secrets.

## Repository layout

- `app.py`, `pages/` — Streamlit presentation and navigation
- `src/solar_design/calculations/` — pure engineering engines
- `src/solar_design/services/` — workflow orchestration and delivery boundaries
- `src/solar_design/exports/` — canonical JSON, Excel, and CSV contracts
- `data/releases/` — versioned reference data and manifests
- `tests/phase1`–`tests/phase11` — contract, engine, UI, export, verification, and release tests
