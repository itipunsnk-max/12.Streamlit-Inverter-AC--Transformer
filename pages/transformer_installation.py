"""Transformer sizing and installation assessment page."""

from pathlib import Path

import streamlit as st

from solar_design.ui.rendering import (
    render_findings,
    render_page_header,
    render_status,
    render_workspace_banner,
)
from solar_design.ui.runtime import get_workspace_state, run_workflow

state = get_workspace_state()
ROOT = Path(__file__).resolve().parents[1]
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
        dimensions = st.columns(4)
        dimensions[0].metric(
            "Pad (m) | ฐานหม้อแปลง",
            " × ".join(str(item) for item in assessment.pad_dimensions_m)
            if assessment.pad_dimensions_m
            else "NOT ASSESSED",
        )
        dimensions[1].metric(
            "Yard (m) | ลานหม้อแปลง",
            " × ".join(str(item) for item in assessment.yard_dimensions_m)
            if assessment.yard_dimensions_m
            else "NOT ASSESSED",
        )
        dimensions[2].metric(
            "Earth conductor (m) | สายดิน",
            assessment.earth_conductor_length_m or "NOT ASSESSED",
        )
        dimensions[3].metric(
            "Earth rods | หลักดิน",
            assessment.earth_rod_count or "NOT ASSESSED",
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

st.subheader("Transformer reference | ภาพอ้างอิงหม้อแปลง")
st.caption(
    "Concept illustrations clarify the equipment chain and yard zones; they are not "
    "construction drawings or utility approval. / ภาพนี้ใช้ช่วยทำความเข้าใจเท่านั้น "
    "ไม่ใช่แบบก่อสร้างหรือการอนุมัติจากการไฟฟ้า"
)
reference_tabs = st.tabs(
    ["Connection chain | ลำดับการเชื่อมต่อ", "Yard concept | แนวคิดลานหม้อแปลง"]
)
with reference_tabs[0]:
    st.image(
        str(ROOT / "assets" / "transformer_single_line_reference.svg"),
        width="stretch",
    )
with reference_tabs[1]:
    st.image(
        str(ROOT / "assets" / "transformer_yard_reference.svg"),
        width="stretch",
    )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_transformer",
    help="Recalculate transformer and installation results from the saved project basis. / "
    "ประมวลผลหม้อแปลงและการติดตั้งใหม่จากข้อมูลโครงการ",
):
    run_workflow()
    st.rerun()
