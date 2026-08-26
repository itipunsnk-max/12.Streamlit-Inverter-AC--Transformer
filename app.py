"""Streamlit entrypoint for the bilingual Phase 11 engineering workflow."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Community Cloud starts the entrypoint from the repository root. Keep the
# src-layout package importable in both an editable checkout and a deployment.
ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from solar_design.ui.rendering import render_disclaimer, render_global_help  # noqa: E402
from solar_design.ui.runtime import initialize_workspace  # noqa: E402

st.set_page_config(
    page_title="Solar Electrical Design | ออกแบบระบบไฟฟ้าโซลาร์",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
initialize_workspace(ROOT / "data" / "releases" / "2026.08-draft")

pages = {
    "Workflow | ลำดับงาน": [
        st.Page(
            "pages/dashboard.py",
            title="Dashboard | ภาพรวม",
            icon=":material/dashboard:",
        ),
        st.Page(
            "pages/project_inputs.py",
            title="Project Inputs | ข้อมูลโครงการ",
            icon=":material/edit_note:",
        ),
        st.Page(
            "pages/inverter_selection.py",
            title="PV / Inverter Selection | อินเวอร์เตอร์",
            icon=":material/solar_power:",
        ),
        st.Page(
            "pages/protection_ampacity.py",
            title="Protection & 70°C Ampacity | ป้องกันและพิกัดกระแส",
            icon=":material/electrical_services:",
        ),
        st.Page(
            "pages/cable_wiring.py",
            title="Cable / PE / Conduit | สายไฟ PE และท่อ",
            icon=":material/cable:",
        ),
        st.Page(
            "pages/transformer_installation.py",
            title="Transformer & Installation | หม้อแปลงและการติดตั้ง",
            icon=":material/bolt:",
        ),
        st.Page(
            "pages/boq_editor.py",
            title="BOQ Editor | ตรวจรายการ",
            icon=":material/receipt_long:",
        ),
        st.Page(
            "pages/cost_summary.py",
            title="Cost Summary | สรุปงบประมาณ",
            icon=":material/payments:",
        ),
    ]
}

current_page = st.navigation(pages, position="sidebar")
render_global_help()
render_disclaimer()
current_page.run()
