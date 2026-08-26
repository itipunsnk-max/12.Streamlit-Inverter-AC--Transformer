"""Workflow dashboard page."""

import streamlit as st

from solar_design.ui.rendering import render_findings, render_page_header, render_workspace_banner
from solar_design.ui.runtime import get_workspace_state, run_workflow

state = get_workspace_state()
render_page_header(
    "Solar Electrical Design",
    "Traceable workflow from project basis through budgetary cost summary.",
    title_th="การออกแบบระบบไฟฟ้าโซลาร์",
    description_th="ลำดับงานที่ตรวจสอบย้อนกลับได้ ตั้งแต่ข้อมูลโครงการถึงสรุปงบประมาณ",
)
render_workspace_banner(state)

st.info(
    "Start at Project Inputs, save the project basis, then run the design workflow. "
    "Results remain visibly STALE after any upstream input change until recalculated. / "
    "เริ่มที่ Project Inputs บันทึกข้อมูล แล้วประมวลผล ผลลัพธ์จะเป็น STALE "
    "เมื่อข้อมูลต้นทางเปลี่ยนจนกว่าจะประมวลผลใหม่"
)

columns = st.columns(4)
columns[0].metric("Project | โครงการ", state.inputs.project_name)
columns[1].metric("Workflow revision | รุ่นการประมวลผล", state.revision)
columns[2].metric("Findings | รายการทบทวน", len(state.findings))
columns[3].metric(
    "Cost summary | สรุปงบประมาณ",
    "READY | พร้อมใช้" if state.results.cost else "NOT RUN | ยังไม่ประมวลผล",
)

st.subheader("Workflow stages | ขั้นตอนการทำงาน")
stage_labels = {
    "INVERTER": "PV / Inverter Selection | อินเวอร์เตอร์",
    "PROTECTION": "Protection | ระบบป้องกัน",
    "AMPACITY": "70°C Ampacity | พิกัดกระแส 70°C",
    "WIRING": "Cable / PE / Conduit | สายไฟ PE และท่อ",
    "TRANSFORMER": "Transformer & Installation | หม้อแปลงและการติดตั้ง",
    "BOQ": "BOQ Editor | ตรวจรายการ",
    "COST": "Cost Summary | สรุปงบประมาณ",
}
for stage, label in stage_labels.items():
    status = "STALE | ต้องประมวลผลใหม่" if state.stage_is_stale(stage) else "CURRENT | เป็นปัจจุบัน"
    st.write(f"**{label}** — {status}")

render_findings(state.findings, title="Warnings and review items | คำเตือนและรายการที่ต้องทบทวน")

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_dashboard",
    type="primary",
    help="Run the coordinated workflow from the saved project basis. / "
    "ประมวลผลตามลำดับงานจากข้อมูลโครงการที่บันทึกแล้ว",
):
    run_workflow()
    st.rerun()
