"""Reusable presentation primitives; no engineering calculations live here."""

from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from solar_design.domain import AssessmentStatus, Finding, FindingSeverity

from .state import WorkspaceState

APP_DISCLAIMER_EN = (
    "Preliminary engineering and budgetary assessment only. Confirm site data, "
    "manufacturer information, utility requirements, protection coordination, and "
    "the final design with the responsible engineer before procurement or construction."
)
APP_DISCLAIMER_TH = (
    "ผลลัพธ์เป็นการประเมินเบื้องต้นด้านวิศวกรรมและงบประมาณเท่านั้น "
    "ต้องยืนยันข้อมูลหน้างาน ข้อมูลผู้ผลิต ข้อกำหนดการไฟฟ้า การประสานการป้องกัน "
    "และแบบฉบับสุดท้ายกับวิศวกรผู้รับผิดชอบก่อนจัดซื้อหรือก่อสร้าง"
)


def render_page_header(
    title: str,
    description: str,
    *,
    title_th: str | None = None,
    description_th: str | None = None,
) -> None:
    """Render a bilingual, text-first heading for keyboard and screen-reader users."""

    st.title(f"{title} | {title_th}" if title_th else title)
    st.caption(description)
    if description_th:
        st.caption(description_th)


def render_global_help() -> None:
    """Render release/help guidance shared by every page."""

    with st.sidebar.expander("Help | ช่วยเหลือ", expanded=False):
        st.markdown(
            "**Workflow** — Start at **Project Inputs | ข้อมูลโครงการ**, save the project "
            "basis, then run the workflow. Review every warning before using the cost summary."
        )
        st.markdown(
            "**ลำดับการใช้งาน** — เริ่มที่ **Project Inputs | ข้อมูลโครงการ** "
            "บันทึกข้อมูล แล้วสั่งประมวลผล ตรวจคำเตือนทั้งหมดก่อนใช้สรุปงบประมาณ"
        )
        st.markdown(
            "**STALE** means an upstream input changed; run the workflow again before relying "
            "on downstream results. / **STALE** หมายถึงข้อมูลต้นทางเปลี่ยน ต้องประมวลผลใหม่"
        )
        st.markdown(
            "Manual overrides require a reason and remain visible in the audit trail. / "
            "การ override ต้องระบุเหตุผลและจะแสดงใน audit trail"
        )


def render_disclaimer() -> None:
    """Render the application safety disclaimer in both languages."""

    with st.container(border=True):
        st.caption(f"Disclaimer | ข้อจำกัดความรับผิดชอบ: {APP_DISCLAIMER_EN}")
        st.caption(APP_DISCLAIMER_TH)


def render_workspace_banner(state: WorkspaceState) -> None:
    if state.reference_error:
        st.error(f"Reference data error | ข้อมูลอ้างอิงผิดพลาด: {state.reference_error}")
    if state.validation_errors:
        for message in state.validation_errors:
            st.error(f"Validation | ตรวจสอบข้อมูล: {message}")
    stale = ", ".join(sorted(state.stale_stages))
    if stale:
        st.warning(
            "STALE | ต้องประมวลผลใหม่ — downstream results require recalculation: "
            f"{stale}"
        )
    st.caption(
        "Reference release | ชุดข้อมูลอ้างอิง: "
        f"{state.reference_snapshot.data_version if state.reference_snapshot else 'unavailable'}"
        f" · Workspace revision | รุ่นข้อมูล: {state.revision}"
    )


def render_findings(
    findings: Iterable[Finding],
    *,
    title: str = "Warnings and review items | คำเตือนและรายการที่ต้องทบทวน",
) -> None:
    findings_tuple = tuple(findings)
    if not findings_tuple:
        st.success("No warnings recorded for this stage. | ไม่พบคำเตือนในขั้นตอนนี้")
        return
    st.subheader(title)
    for finding in findings_tuple:
        message = f"{finding.code}: {finding.message}"
        if finding.severity is FindingSeverity.BLOCKER:
            st.error(message)
        elif finding.severity in {FindingSeverity.REVIEW, FindingSeverity.WARNING}:
            st.warning(message)
        else:
            st.info(message)


def render_status(status: AssessmentStatus | None, *, label: str = "Status | สถานะ") -> None:
    value = status.value if status is not None else "NOT_RUN"
    if status is AssessmentStatus.PASS:
        st.success(f"{label}: {value}")
    elif status is AssessmentStatus.FAIL or status is AssessmentStatus.MISSING:
        st.error(f"{label}: {value}")
    else:
        st.info(f"{label}: {value}")


def render_run_button(*, key: str = "run_workflow") -> bool:
    return st.button("Run design workflow | ประมวลผลการออกแบบ", key=key, type="primary")
