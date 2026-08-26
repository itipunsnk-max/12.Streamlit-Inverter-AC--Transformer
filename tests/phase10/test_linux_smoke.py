"""Linux-compatible, non-Streamlit workflow smoke test for CI."""

from __future__ import annotations

from pathlib import Path

from solar_design.repositories import ReleaseRepository
from solar_design.services.workflow import ProjectInputs, run_design_workflow

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def test_linux_smoke_loads_release_and_runs_full_workflow_without_ui() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    results = run_design_workflow(ProjectInputs(), snapshot, revision=0)

    assert results.inverter is not None
    assert results.transformer is not None
    assert results.boq is not None
    assert results.cost is not None
