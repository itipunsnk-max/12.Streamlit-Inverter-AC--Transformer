"""Protection and strict 70°C ampacity result page."""

import streamlit as st

from solar_design.ui.rendering import (
    render_findings,
    render_page_header,
    render_status,
    render_workspace_banner,
)
from solar_design.ui.runtime import get_workspace_state, run_workflow

state = get_workspace_state()
render_page_header(
    "Protection & 70°C Ampacity",
    "Protection remains assessment-only until fault and coordination data are approved.",
    title_th="ระบบป้องกันและพิกัดกระแส 70°C",
    description_th="ระบบป้องกันเป็นผลประเมินจนกว่าจะมีข้อมูล fault และ coordination ที่อนุมัติ",
)
render_workspace_banner(state)

if state.results.protection is None and state.results.ampacity is None:
    st.info(
        "Run the design workflow from Project Inputs to populate this page. / "
        "สั่งประมวลผลจาก Project Inputs เพื่อแสดงผลหน้านี้"
    )
else:
    protection = state.results.protection
    ampacity = state.results.ampacity
    if protection:
        render_status(protection.status, label="Protection | ระบบป้องกัน")
        st.write(f"Load current | กระแสโหลด: **{protection.load_current_a} A**")
        st.write(
            "Selected breaker | เบรกเกอร์ที่เลือก: "
            f"**{protection.selected_breaker_id or 'NOT ASSESSED'}**"
        )
        render_findings(
            protection.findings,
            title="Protection findings | รายการทบทวนระบบป้องกัน",
        )
    if ampacity:
        render_status(ampacity.status, label="Strict 70°C ampacity | พิกัดกระแส 70°C")
        columns = st.columns(3)
        columns[0].metric(
            "Required ampacity (A) | พิกัดกระแสที่ต้องการ",
            ampacity.strict_70c_required_ampacity_a,
        )
        columns[1].metric(
            "Available corrected (A) | พิกัดกระแสหลังปรับแก้",
            ampacity.available_corrected_ampacity_a,
        )
        columns[2].metric(
            "Estimated temperature (°C) | อุณหภูมิประมาณการ",
            ampacity.estimated_conductor_temperature_c or "N/A | ไม่มีข้อมูล",
        )
        render_findings(
            ampacity.findings,
            title="Ampacity findings | รายการทบทวนพิกัดกระแส",
        )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_protection",
    help="Recalculate protection and ampacity from the saved project basis. / "
    "ประมวลผลระบบป้องกันและพิกัดกระแสใหม่จากข้อมูลโครงการ",
):
    run_workflow()
    st.rerun()
