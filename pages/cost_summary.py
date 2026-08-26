"""Low/Base/High budgetary cost summary page."""

import streamlit as st

from solar_design.costing import CostScenario
from solar_design.ui.rendering import render_findings, render_page_header, render_workspace_banner
from solar_design.ui.runtime import get_workspace_state, run_workflow

state = get_workspace_state()
render_page_header(
    "Cost Summary",
    "Review the Decimal cost revision and its traceable findings; "
    "the waterfall stays in the costing engine.",
    title_th="สรุปงบประมาณ",
    description_th="ตรวจสอบต้นทุนและรายการทบทวนที่ตรวจสอบย้อนกลับได้ โดยการคำนวณอยู่ใน costing engine",
)
render_workspace_banner(state)

cost = state.results.cost
if cost is None:
    st.info(
        "Run the design workflow from Project Inputs to populate this page. / "
        "สั่งประมวลผลจาก Project Inputs เพื่อแสดงผลหน้านี้"
    )
else:
    rows = []
    for scenario in CostScenario:
        total = cost.total_for(scenario)
        rows.append(
            {
                "Scenario | กรณีราคา": scenario.value,
                "Direct cost (THB) | ต้นทุนตรง": str(total.direct_cost),
                "Subtotal before VAT (THB) | รวมก่อน VAT": str(total.subtotal_before_vat),
                "VAT (THB) | ภาษีมูลค่าเพิ่ม": str(total.vat),
                "Grand total (THB) | ยอดรวมสุทธิ": str(total.grand_total),
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)
    base = cost.total_for(CostScenario.BASE)
    st.metric("Base grand total (THB) | ยอดรวมกรณีฐาน", str(base.grand_total))
    render_findings(
        cost.findings,
        title="Cost findings | รายการทบทวนต้นทุน",
    )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_cost",
    help="Recalculate the cost summary from the saved project basis. / "
    "ประมวลผลสรุปงบประมาณใหม่จากข้อมูลโครงการที่บันทึกแล้ว",
):
    run_workflow()
    st.rerun()
