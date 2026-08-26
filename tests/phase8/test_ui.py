"""Phase 8 coordinator and Streamlit AppTest coverage."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from solar_design.costing import CostScenario
from solar_design.ui.state import WORKFLOW_STAGES, WorkspaceCoordinator

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def test_workspace_coordinator_runs_from_inputs_to_cost_summary() -> None:
    coordinator = WorkspaceCoordinator(RELEASE)
    state = coordinator.initial_state()

    assert state.reference_snapshot is not None
    assert len(state.inverter_options) > 0
    assert state.stale_stages == frozenset(WORKFLOW_STAGES)

    state = coordinator.run_workflow(state)

    assert state.validation_errors == ()
    assert state.stale_stages == frozenset()
    assert state.results.inverter is not None
    assert state.results.transformer is not None
    assert state.results.boq is not None
    assert state.results.cost is not None
    assert state.results.cost.total_for(CostScenario.BASE).grand_total >= 0


def test_saving_changed_inputs_marks_downstream_results_stale_and_keeps_override_reason() -> None:
    coordinator = WorkspaceCoordinator(RELEASE)
    state = coordinator.run_workflow(coordinator.initial_state())
    changed = coordinator.save_inputs(
        state,
        {
            "project_name": "Changed basis",
            "required_dc_power_kwp": 120,
            "required_ac_voltage_v": None,
            "load_kw": 100,
            "power_factor": 0.95,
            "demand_factor": 0.8,
            "spare_percent": 10,
            "derating_factor": 0.95,
            "installation_type": "YARD",
            "transformer_count": 1,
            "duty": "EQUAL_SHARING",
            "high_voltage_v": 22000,
            "low_voltage_v": 400,
            "override_inverter_model_id": "",
            "override_transformer_rating_kva": 500,
            "override_reason": "Owner selected available transformer rating",
        },
    )

    assert changed.validation_errors == ()
    assert changed.stale_stages == frozenset(WORKFLOW_STAGES)
    assert changed.override_reasons == (
        ("TRANSFORMER", "Owner selected available transformer rating"),
    )


def test_project_inputs_validation_requires_override_reason() -> None:
    coordinator = WorkspaceCoordinator(RELEASE)
    state = coordinator.initial_state()
    updated = coordinator.save_inputs(
        state,
        {
            "project_name": "Invalid override",
            "required_dc_power_kwp": 100,
            "required_ac_voltage_v": None,
            "load_kw": 100,
            "power_factor": 0.95,
            "demand_factor": 0.8,
            "spare_percent": 10,
            "derating_factor": 0.95,
            "installation_type": "YARD",
            "transformer_count": 1,
            "duty": "EQUAL_SHARING",
            "high_voltage_v": 22000,
            "low_voltage_v": 400,
            "override_inverter_model_id": "INV-SUNGROW-SG125CX-P2",
            "override_transformer_rating_kva": 0,
            "override_reason": "",
        },
    )

    assert any("override reason" in item.lower() for item in updated.validation_errors)


def test_streamlit_app_landing_page_runs() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

    assert not app.exception
    assert app.title
    assert any("Solar Electrical Design" in item.value for item in app.title)


def test_streamlit_navigation_reaches_project_inputs_and_cost_summary() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

    app.switch_page("pages/project_inputs.py").run()
    assert not app.exception
    assert any("Project Inputs" in item.value for item in app.title)

    app.switch_page("pages/cost_summary.py").run()
    assert not app.exception
    assert any("Cost Summary" in item.value for item in app.title)


def test_streamlit_all_phase8_pages_render_without_exceptions() -> None:
    page_paths = (
        "pages/dashboard.py",
        "pages/project_inputs.py",
        "pages/inverter_selection.py",
        "pages/protection_ampacity.py",
        "pages/cable_wiring.py",
        "pages/transformer_installation.py",
        "pages/boq_editor.py",
        "pages/cost_summary.py",
    )
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    for page_path in page_paths:
        app.switch_page(page_path).run()
        assert not app.exception, page_path


def test_streamlit_project_input_change_exposes_stale_and_override_validation() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    app.switch_page("pages/project_inputs.py").run()

    app.number_input("required_dc_power_kwp").set_value(120)
    next(
        item
        for item in app.button
        if item.label == "Save Project Inputs | บันทึกข้อมูลโครงการ"
    ).click().run()
    assert not app.exception
    assert any("STALE" in item.value for item in app.warning)

    app.selectbox("override_inverter_model_id").set_value("INV-SUNGROW-SG125CX-P2")
    app.text_area("override_reason").set_value("")
    next(
        item
        for item in app.button
        if item.label == "Save Project Inputs | บันทึกข้อมูลโครงการ"
    ).click().run()
    assert any("override reason" in item.value.lower() for item in app.error)
