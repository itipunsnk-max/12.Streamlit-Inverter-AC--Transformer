"""PV and inverter result page."""

import streamlit as st

from solar_design.services.reference_views import inverter_wiring_references
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

st.subheader("Independent inverter reference | ตารางอ้างอิงอินเวอร์เตอร์แบบไม่ต้อง Run")
st.caption(
    "Manufacturer fields are shown with a one-inverter-to-one-feeder 70°C assessment. "
    "MISSING means the current exact catalogue chain is incomplete. / "
    "แสดงข้อมูลผู้ผลิตและผลประเมินสายป้อนแยกต่ออินเวอร์เตอร์หนึ่งตัว โดย MISSING "
    "หมายถึงข้อมูล exact ในชุดอ้างอิงยังไม่ครบ"
)
if state.reference_snapshot is not None:
    references = inverter_wiring_references(state.reference_snapshot)
    selected_id = st.selectbox(
        "Reference model | รุ่นที่ต้องการดู",
        options=[item.inverter_id for item in references],
        format_func=lambda item_id: next(
            f"{item.manufacturer} {item.model}"
            for item in references
            if item.inverter_id == item_id
        ),
        key="inverter_reference_model",
    )
    reference = next(item for item in references if item.inverter_id == selected_id)
    details = st.columns(4)
    details[0].metric("Rated AC | กำลังพิกัด", f"{reference.rated_ac_kw} kW")
    details[1].metric(
        "Max AC current | กระแสสูงสุด",
        f"{reference.maximum_ac_current_a or 'MISSING'} A",
    )
    details[2].metric(
        "DC / startup | แรงดัน DC / เริ่มทำงาน",
        f"{reference.dc_max_voltage_v or 'MISSING'} / "
        f"{reference.startup_voltage_v or 'MISSING'} V",
    )
    details[3].metric(
        "MPPT | จำนวน MPPT",
        reference.mppt_count or "MISSING",
    )
    st.write(
        f"**{reference.model}** → "
        f"**Main {reference.main_cable_csa_mm2 or 'MISSING'} mm² × "
        f"{reference.parallel_runs or 'MISSING'} set(s)** → "
        f"**PE {reference.pe_cable_csa_mm2 or 'MISSING'} mm²** → "
        f"**IMC {reference.conduit_trade_size or 'MISSING'} × "
        f"{reference.conduit_count or 'MISSING'} conduit(s)**"
    )
    required_ampacity_text = (
        f"{reference.required_70c_ampacity_a:.2f}"
        if reference.required_70c_ampacity_a is not None
        else "MISSING"
    )
    actual_fill_text = (
        f"{reference.maximum_actual_fill_percent:.2f}"
        if reference.maximum_actual_fill_percent is not None
        else "MISSING"
    )
    fill_limit_text = (
        f"{reference.permitted_fill_percent:.0f}"
        if reference.permitted_fill_percent is not None
        else "MISSING"
    )
    st.caption(
        f"AC connection: {reference.ac_connection or 'MISSING'} · "
        f"70°C required ampacity: {required_ampacity_text} A · "
        f"cables per conduit: {reference.conductors_per_conduit or 'MISSING'} · "
        f"fill: {actual_fill_text}% / limit {fill_limit_text}%"
    )
    if reference.status.value == "MISSING":
        st.warning(
            "This model is visible for external selection, but PE/conduit remains "
            "MISSING/REVIEW until the exact catalogue chain is complete. / "
            "รุ่นนี้เลือกดูได้ แต่ PE/ท่อยังเป็น MISSING/REVIEW จนกว่าข้อมูล exact จะครบ"
        )
    if reference.review_items:
        with st.expander("Reference review items | รายการที่ต้องทบทวน"):
            for item in reference.review_items:
                st.write(f"- {item}")

    with st.expander("All inverter manufacturer fields | ข้อมูลผู้ผลิตทุกรุ่น"):
        st.dataframe(
            [
                {
                    "inverter_id": item.inverter_id,
                    "manufacturer": item.manufacturer,
                    "model": item.model,
                    "rated_ac_kw": item.rated_ac_kw,
                    "ac_voltage_v": item.ac_voltage_v,
                    "max_ac_current_a": item.maximum_ac_current_a,
                    "dc_max_v": item.dc_max_voltage_v,
                    "startup_v": item.startup_voltage_v,
                    "mppt_range_v": item.mppt_range_v,
                    "mppt_qty": item.mppt_count,
                    "inputs_per_mppt": item.inputs_per_mppt,
                    "max_i_mppt_a": item.maximum_input_current_per_mppt_a,
                    "max_isc_mppt_a": item.maximum_short_circuit_current_per_mppt_a,
                }
                for item in references
            ],
            width="stretch",
            hide_index=True,
        )
    with st.expander("All 70°C feeder results | ผลสายป้อน 70°C ทุกรุ่น"):
        st.dataframe(
            [
                {
                    "model": item.model,
                    "status": item.status.value,
                    "required_70c_a": item.required_70c_ampacity_a,
                    "main_csa_mm2": item.main_cable_csa_mm2,
                    "parallel_sets": item.parallel_runs,
                    "PE_csa_mm2": item.pe_cable_csa_mm2,
                    "conductors_per_conduit": item.conductors_per_conduit,
                    "IMC_trade_size": item.conduit_trade_size,
                    "conduit_count": item.conduit_count,
                    "fill_percent": item.maximum_actual_fill_percent,
                    "fill_limit_percent": item.permitted_fill_percent,
                }
                for item in references
            ],
            width="stretch",
            hide_index=True,
        )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_inverter",
    help="Recalculate this page from the saved project basis. / "
    "ประมวลผลหน้านี้ใหม่จากข้อมูลโครงการที่บันทึกแล้ว",
):
    run_workflow()
    st.rerun()
