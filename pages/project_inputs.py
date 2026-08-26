"""Project basis and workflow execution page."""

import streamlit as st

from solar_design.domain import TransformerDuty
from solar_design.ui.rendering import render_page_header, render_workspace_banner
from solar_design.ui.runtime import get_workspace_state, run_workflow, update_inputs

state = get_workspace_state()
render_page_header(
    "Project Inputs",
    "Enter the project basis and explicit manual overrides. Engineering rules stay in the engines.",
    title_th="ข้อมูลโครงการ",
    description_th="กรอกข้อมูลตั้งต้นและ override ที่ผู้ใช้ยืนยัน กฎวิศวกรรมอยู่ใน calculation engine",
)
render_workspace_banner(state)

option_ids = [""] + [item[0] for item in state.inverter_options]
option_labels = {"": "Automatic selection"} | dict(state.inverter_options)
current_override = state.inputs.override_inverter_model_id or ""
current_index = option_ids.index(current_override) if current_override in option_ids else 0

with st.form("project_inputs_form"):
    st.subheader("Project basis | ข้อมูลตั้งต้นโครงการ")
    project_name = st.text_input(
        "Project name | ชื่อโครงการ",
        value=state.inputs.project_name,
        key="project_name",
        help="A human-readable name used in the workspace and export metadata. / "
        "ชื่อสำหรับแสดงใน workspace และ metadata ของไฟล์ส่งออก",
    )
    required_dc = st.number_input(
        "Required DC power (kWp) | กำลังไฟ DC ที่ต้องการ",
        min_value=0.0,
        value=float(state.inputs.required_dc_power_kwp),
        step=1.0,
        key="required_dc_power_kwp",
        help="Enter the required project DC capacity. / กรอกกำลังไฟ DC ที่ต้องการของโครงการ",
    )
    specify_voltage = st.checkbox(
        "Specify AC voltage | ระบุแรงดัน AC",
        value=state.inputs.required_ac_voltage_v is not None,
        key="specify_ac_voltage",
        help="Enable only when the project basis provides a specific AC voltage. / "
        "เปิดเมื่อมีข้อมูลแรงดัน AC ของโครงการ",
    )
    ac_voltage = st.number_input(
        "AC voltage (V) | แรงดัน AC",
        min_value=0.0,
        value=float(state.inputs.required_ac_voltage_v or 400),
        step=1.0,
        disabled=not specify_voltage,
        key="required_ac_voltage_v",
        help=(
            "Optional AC voltage supplied by the project basis. / "
            "แรงดัน AC ที่ระบุในข้อมูลโครงการ (ไม่บังคับ)"
        ),
    )
    load_kw = st.number_input(
        "Demand load (kW) | โหลดที่ใช้พิจารณา",
        min_value=0.0,
        value=float(state.inputs.load_kw),
        step=1.0,
        key="load_kw",
        help=(
            "Enter the project load basis; the calculation engine applies the configured "
            "assumptions. / กรอกโหลดตั้งต้นของโครงการ โดย engine จะใช้สมมติฐานที่กำหนด"
        ),
    )
    power_factor = st.number_input(
        "Power factor | ตัวประกอบกำลัง",
        min_value=0.0,
        max_value=1.0,
        value=float(state.inputs.power_factor),
        step=0.01,
        key="power_factor",
        help="Use the approved project power factor. / ใช้ตัวประกอบกำลังที่ได้รับการยืนยัน",
    )
    demand_factor = st.number_input(
        "Demand factor | ตัวประกอบการใช้โหลด",
        min_value=0.0,
        max_value=1.0,
        value=float(state.inputs.demand_factor),
        step=0.01,
        key="demand_factor",
        help="Use the approved project demand factor. / ใช้ตัวประกอบการใช้โหลดที่ได้รับการยืนยัน",
    )
    spare_percent = st.number_input(
        "Spare (%) | เผื่อกำลัง",
        min_value=0.0,
        value=float(state.inputs.spare_percent),
        step=1.0,
        key="spare_percent",
        help="Enter the approved spare allowance as a percentage. / กรอกค่ากำลังสำรองเป็นเปอร์เซ็นต์",
    )
    derating_factor = st.number_input(
        "Derating factor | ตัวคูณลดทอน",
        min_value=0.0,
        max_value=1.0,
        value=float(state.inputs.derating_factor),
        step=0.01,
        key="derating_factor",
        help="Use the approved project derating factor. / ใช้ตัวคูณลดทอนที่ได้รับการยืนยัน",
    )

    st.subheader("Transformer basis | ข้อมูลตั้งต้นหม้อแปลง")
    installation_type = st.selectbox(
        "Installation type | ประเภทการติดตั้ง",
        ["YARD", "POLE_MOUNTED"],
        index=0 if state.inputs.installation_type == "YARD" else 1,
        key="installation_type",
        help="Select the installation category represented in the approved project basis. / "
        "เลือกประเภทการติดตั้งตามข้อมูลโครงการที่ยืนยัน",
    )
    transformer_count = st.number_input(
        "Transformer count | จำนวนหม้อแปลง",
        min_value=1,
        value=state.inputs.transformer_count,
        step=1,
        key="transformer_count",
        help="Enter the number of transformer units in the project basis. / "
        "กรอกจำนวนหม้อแปลงตามข้อมูลโครงการ",
    )
    duty = st.selectbox(
        "Duty basis | หลักเกณฑ์การใช้งาน",
        [item.value for item in TransformerDuty],
        index=[item.value for item in TransformerDuty].index(state.inputs.duty.value),
        key="duty",
        help=(
            "Select the approved transformer duty basis; unsupported combinations remain "
            "under review. / เลือกหลักเกณฑ์ที่ยืนยันแล้ว หากชุดข้อมูลไม่รองรับจะแสดงให้ทบทวน"
        ),
    )
    high_voltage = st.number_input(
        "HV voltage (V) | แรงดันด้าน HV",
        min_value=0.0,
        value=float(state.inputs.high_voltage_v),
        step=100.0,
        key="high_voltage_v",
        help="Enter the high-voltage basis in volts. / กรอกแรงดันด้าน HV เป็นโวลต์",
    )
    low_voltage = st.number_input(
        "LV voltage (V) | แรงดันด้าน LV",
        min_value=0.0,
        value=float(state.inputs.low_voltage_v),
        step=10.0,
        key="low_voltage_v",
        help="Enter the low-voltage basis in volts. / กรอกแรงดันด้าน LV เป็นโวลต์",
    )

    st.subheader("Manual overrides | การ override โดยผู้ใช้")
    override_inverter = st.selectbox(
        "Inverter override | เลือกอินเวอร์เตอร์แทนระบบอัตโนมัติ",
        option_ids,
        index=current_index,
        format_func=lambda value: option_labels[value],
        key="override_inverter_model_id",
        help="Leave automatic selection unless an owner-approved override is required. / "
        "เว้นว่างเพื่อใช้การเลือกอัตโนมัติ เว้นแต่มีการอนุมัติให้ override",
    )
    override_transformer = st.number_input(
        "Transformer rating override per unit (kVA; 0 = none) | override ขนาดต่อเครื่อง",
        min_value=0.0,
        value=float(state.inputs.override_transformer_rating_kva or 0),
        step=10.0,
        key="override_transformer_rating_kva",
        help="Use 0 when no override is requested. A reason is required for a non-zero value. / "
        "ใช้ 0 เมื่อไม่ override และต้องระบุเหตุผลเมื่อกรอกค่าอื่น",
    )
    override_reason = st.text_area(
        "Override reason | เหตุผลการ override",
        value=state.inputs.override_reason or "",
        key="override_reason",
        help="Record the owner-approved reason and evidence for any manual override. / "
        "บันทึกเหตุผลและหลักฐานการอนุมัติสำหรับการ override",
    )
    save = st.form_submit_button(
        "Save Project Inputs | บันทึกข้อมูลโครงการ",
        type="primary",
        help="Save inputs and mark downstream results STALE when the basis changes. / "
        "บันทึกข้อมูล และทำให้ผลลัพธ์ปลายทางเป็น STALE เมื่อข้อมูลตั้งต้นเปลี่ยน",
    )

if save:
    updated = update_inputs(
        {
            "project_name": project_name,
            "required_dc_power_kwp": required_dc,
            "required_ac_voltage_v": ac_voltage if specify_voltage else None,
            "load_kw": load_kw,
            "power_factor": power_factor,
            "demand_factor": demand_factor,
            "spare_percent": spare_percent,
            "derating_factor": derating_factor,
            "installation_type": installation_type,
            "transformer_count": transformer_count,
            "duty": duty,
            "high_voltage_v": high_voltage,
            "low_voltage_v": low_voltage,
            "override_inverter_model_id": override_inverter,
            "override_transformer_rating_kva": override_transformer,
            "override_reason": override_reason,
        }
    )
    if updated.validation_errors:
        for error in updated.validation_errors:
            st.error(f"Validation | ตรวจสอบข้อมูล: {error}")
    else:
        st.success(
            "Project Inputs saved. Downstream results are now STALE until recalculated. / "
            "บันทึกข้อมูลแล้ว ผลลัพธ์ปลายทางเป็น STALE จนกว่าจะประมวลผลใหม่"
        )

if st.button(
    "Run design workflow | ประมวลผลการออกแบบ",
    key="run_workflow_from_inputs",
    type="primary",
    help="Run the coordinated workflow using the saved project basis. / "
    "ประมวลผลตามลำดับงานด้วยข้อมูลโครงการที่บันทึกแล้ว",
):
    updated = run_workflow()
    if updated.validation_errors:
        for error in updated.validation_errors:
            st.error(f"Validation | ตรวจสอบข้อมูล: {error}")
    else:
        st.success(
            "Workflow completed. Review warnings before using the budgetary summary. / "
            "ประมวลผลเสร็จแล้ว ตรวจคำเตือนก่อนใช้สรุปงบประมาณ"
        )
