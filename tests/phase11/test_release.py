"""Phase 11 bilingual UX, accessibility, and release-document contracts."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]


def test_readme_and_release_docs_define_the_safety_and_rollback_boundary() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    deployment = (ROOT / "docs" / "DEPLOYMENT.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "preliminary" in readme.lower()
    assert "วิศวกรผู้รับผิดชอบ" in readme
    assert "Community Cloud" in deployment
    assert "restricted-access" in deployment.lower()
    assert "Rollback" in deployment
    assert "Only specific people can view this app" in deployment
    assert "No formula" in checklist
    assert "Streamlit AppTest" in checklist
    assert "Tablet viewport" in checklist


def test_repo_release_contract_keeps_secrets_out_of_git() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert ".streamlit/secrets.toml" in gitignore
    assert "secrets.toml" not in requirements
    assert not (ROOT / ".streamlit" / "secrets.toml").exists()


def test_streamlit_entrypoint_renders_bilingual_notice_and_help() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

    assert not app.exception
    assert any("Solar Electrical Design" in item.value for item in app.title)
    assert any("Disclaimer" in item.value for item in app.caption)
    assert any("ข้อจำกัดความรับผิดชอบ" in item.value for item in app.caption)
    assert "render_global_help" in (ROOT / "app.py").read_text(encoding="utf-8")


def test_all_streamlit_pages_have_bilingual_titles_and_descriptive_actions() -> None:
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
        assert any("|" in item.value for item in app.title), page_path
        assert any("Run design workflow" in item.label for item in app.button), page_path
