"""PV and inverter result page."""

import streamlit as st

from solar_design.ui.rendering import (
    render_findings,
    render_page_header,
    render_workspace_banner,
)
from solar_design.ui.runtime import get_workspace_state, run_workflow

state = get_workspace_state()
render_page_header(
    "PV / Inverter Selection",
    "Review the selected model and its traceable decision findings.",
    title_th="การเลือก PV / อินเวอร์เตอร์",
    description_th="ตรวจสอบรุ่นที่เลือกและรายการทบทวนที่ตรวจสอบย้อนกลับได้",
)
render_workspace_banner(state)
result = state.results.inverter
if result is None:
    st.info(
        "Run the design workflow from Project Inputs to populate this page. / "
        "สั่งประมวลผลจาก Project Inputs เพื่อแสดงผลหน้านี้"
    )
elif state.stage_is_stale("INVERTER"):
    st.warning(
        "The displayed inverter result belongs to an earlier project basis. / "
        "ผลอินเวอร์เตอร์ที่แสดงมาจากข้อมูลโครงการชุดก่อนหน้า"
    )
else:
    st.write(
        f"Selected model | รุ่นที่เลือก: **{result.selected_model_id or 'None'}**"
    )
    columns = st.columns(3)
    columns[0].metric("Quantity | จำนวน", result.quantity)
    columns[1].metric(
        "AC power (kW) | กำลังไฟ AC",
        result.total_ac_power_kw or "Not assessed | ยังไม่ประเมิน",
    )
    columns[2].metric(
        "DC capacity (kWp) | กำลังไฟ DC",
        result.total_dc_capacity_kwp or "Not assessed | ยังไม่ประเมิน",
    )
    render_findings(
        result.findings,
        title="Warnings and review items | คำเตือนและรายการที่ต้องทบทวน",
    )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_inverter",
    help="Recalculate this page from the saved project basis. / "
    "ประมวลผลหน้านี้ใหม่จากข้อมูลโครงการที่บันทึกแล้ว",
):
    run_workflow()
    st.rerun()
