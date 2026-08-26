"""Cable, PE, and conduit result page."""

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
    "Cable / PE / Conduit",
    "Review exact PE lookup, cable selection, and whole-cable conduit allocation results.",
    title_th="สายไฟ / PE / ท่อร้อยสาย",
    description_th="ตรวจสอบการค้นหา PE แบบ exact การเลือกสาย และการจัดสรรสายเต็มเส้นลงท่อ",
)
render_workspace_banner(state)

wiring = state.results.wiring
if wiring is None:
    st.info(
        "Run the design workflow from Project Inputs to populate this page. / "
        "สั่งประมวลผลจาก Project Inputs เพื่อแสดงผลหน้านี้"
    )
else:
    render_status(wiring.cable.status, label="Cable | สายไฟ")
    cable = wiring.cable
    columns = st.columns(4)
    columns[0].metric("Cable | สายไฟ", cable.cable_id or "MISSING | ไม่พบข้อมูล")
    columns[1].metric("Parallel runs | จำนวนชุดขนาน", cable.parallel_runs)
    columns[2].metric(
        "Ampacity / run (A) | พิกัดกระแสต่อชุด",
        cable.ampacity_per_run_a or "MISSING | ไม่พบข้อมูล",
    )
    columns[3].metric(
        "Total ampacity (A) | พิกัดกระแสรวม",
        cable.total_ampacity_a or "MISSING | ไม่พบข้อมูล",
    )

    render_status(wiring.protective_earth.status, label="Protective earth | สายดิน PE")
    st.write(
        "PE CSA | ขนาดหน้าตัดสายดิน: "
        f"**{wiring.protective_earth.pe_cross_section_mm2 or 'MISSING'} mm²**"
    )
    render_findings(wiring.cable.findings, title="Cable findings | รายการทบทวนสายไฟ")
    render_findings(
        wiring.protective_earth.findings,
        title="PE findings | รายการทบทวนสายดิน",
    )
    render_findings(wiring.findings, title="Wiring assessment | ผลประเมินการเดินสาย")

    if state.results.conduit:
        conduit = state.results.conduit
        render_status(conduit.status, label="Conduit | ท่อร้อยสาย")
        st.write(
            f"Conduit | ท่อ: **{conduit.conduit_id or 'MISSING | ไม่พบข้อมูล'}**"
        )
        st.write(f"Runs allocated | จำนวนชุดที่จัดสรร: **{len(conduit.runs)}**")
        render_findings(
            conduit.findings,
            title="Conduit findings | รายการทบทวนท่อร้อยสาย",
        )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_wiring",
    help="Recalculate cable, PE, and conduit results from the saved project basis. / "
    "ประมวลผลสายไฟ PE และท่อใหม่จากข้อมูลโครงการ",
):
    run_workflow()
    st.rerun()
