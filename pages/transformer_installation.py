"""Transformer sizing and installation assessment page."""

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
    "Transformer & Installation",
    "Review standard rating, HV/LV current, duty basis, and explicit installation assessment.",
    title_th="หม้อแปลงและการติดตั้ง",
    description_th="ตรวจสอบขนาดมาตรฐาน กระแส HV/LV หลักเกณฑ์การใช้งาน และผลประเมินการติดตั้ง",
)
render_workspace_banner(state)

result = state.results.transformer
if result is None:
    st.info(
        "Run the design workflow from Project Inputs to populate this page. / "
        "สั่งประมวลผลจาก Project Inputs เพื่อแสดงผลหน้านี้"
    )
else:
    render_status(result.status, label="Transformer sizing | การกำหนดขนาดหม้อแปลง")
    columns = st.columns(4)
    columns[0].metric("Duty | หลักเกณฑ์", result.duty.value)
    columns[1].metric("Count | จำนวนเครื่อง", result.transformer_count)
    columns[2].metric(
        "Selected rating / unit (kVA) | ขนาดต่อเครื่อง",
        result.selected_rating_per_unit_kva or "MISSING | ไม่พบข้อมูล",
    )
    columns[3].metric(
        "Installation | การติดตั้ง",
        result.installation_status.value,
    )
    st.write(
        "HV current / unit | กระแส HV ต่อเครื่อง: "
        f"**{result.high_voltage_current_per_unit_a or 'NOT ASSESSED'} A**"
    )
    st.write(
        "LV current / unit | กระแส LV ต่อเครื่อง: "
        f"**{result.low_voltage_current_per_unit_a or 'NOT ASSESSED'} A**"
    )
    if result.installation_assessment:
        assessment = result.installation_assessment
        st.write(
            "Installation rule | เกณฑ์การติดตั้ง: "
            f"**{assessment.rule_id or 'NOT ASSESSED'}**"
        )
        render_findings(
            assessment.findings,
            title="Installation findings | รายการทบทวนการติดตั้ง",
        )
    render_findings(
        result.findings,
        title="Transformer findings | รายการทบทวนหม้อแปลง",
    )
    if state.override_reasons:
        st.info(
            "Manual override reasons are retained in WorkspaceState. / "
            "เหตุผลการ override ถูกเก็บไว้ใน WorkspaceState"
        )
        for scope, reason in state.override_reasons:
            st.write(f"{scope}: {reason}")

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_transformer",
    help="Recalculate transformer and installation results from the saved project basis. / "
    "ประมวลผลหม้อแปลงและการติดตั้งใหม่จากข้อมูลโครงการ",
):
    run_workflow()
    st.rerun()
