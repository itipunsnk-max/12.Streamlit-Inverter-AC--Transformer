"""BOQ review page backed by the immutable Phase 6 revision."""

import streamlit as st

from solar_design.ui.rendering import render_findings, render_page_header, render_workspace_banner
from solar_design.ui.runtime import get_workspace_state, run_workflow

state = get_workspace_state()
render_page_header(
    "BOQ Editor",
    "Review the deterministic BOQ revision. User deltas remain separate "
    "from regenerated baselines.",
    title_th="ตรวจรายการ BOQ",
    description_th="ตรวจสอบรายการ BOQ ที่สร้างแบบ deterministic โดยการแก้ไขของผู้ใช้แยกจาก baseline",
)
render_workspace_banner(state)

boq = state.results.boq
if boq is None:
    st.info(
        "Run the design workflow from Project Inputs to populate this page. / "
        "สั่งประมวลผลจาก Project Inputs เพื่อแสดงผลหน้านี้"
    )
else:
    st.write(f"BOQ revision | รุ่น BOQ: **{boq.revision_id}**")
    rows = [
        {
            "Line | รายการ": line.line_id,
            "Description | รายละเอียด": f"{line.description_en} | {line.description_th}",
            "Quantity | จำนวน": str(line.quantity),
            "Unit | หน่วย": line.unit,
            "Status | สถานะ": line.cost_status.value,
            "Pricing mode | รูปแบบราคา": line.pricing_mode.value,
            "Included | รวมคำนวณ": line.is_effectively_included,
        }
        for line in boq.lines
    ]
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Included | รวมคำนวณ": st.column_config.CheckboxColumn(
                "Included | รวมคำนวณ",
                help="Whether the line is included in the calculated scope. / "
                "รายการนี้ถูกรวมอยู่ในขอบเขตคำนวณหรือไม่",
            )
        },
    )
    render_findings(boq.findings, title="BOQ findings | รายการทบทวน BOQ")

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_boq",
    help="Regenerate the BOQ and cost results from the saved project basis. / "
    "สร้าง BOQ และต้นทุนใหม่จากข้อมูลโครงการที่บันทึกแล้ว",
):
    run_workflow()
    st.rerun()
