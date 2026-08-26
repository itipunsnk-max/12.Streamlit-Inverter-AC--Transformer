"""Acceptance tests for the Phase 0 repository audit only.

These tests intentionally do not import production application modules.  They
verify the frozen source inventory and planning-document traceability required
before Phase 1 may be assessed.
"""

from __future__ import annotations

import csv
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"
SOURCE_REGISTRY = RELEASE / "sources.csv"
RULE_MATRIX = ROOT / "docs" / "ENGINEERING_RULE_MATRIX.md"
PHASE0_DOCS = (
    ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
    RULE_MATRIX,
    ROOT / "docs" / "DATA_MODEL.md",
)
ENGINEERING_PREFIXES = ("SRC-INV-", "SRC-AMP-", "SRC-WIR-", "SRC-TRF-")
RULE_ID_PATTERN = r"(?:INV|AMP|PRO|CAB|PE|CON|TRF|INS|YARD|GND|BOQ|CST)-\d{3}"


def _source_rows() -> list[dict[str, str]]:
    with SOURCE_REGISTRY.open(encoding="utf-8-sig", newline="") as source_file:
        return list(csv.DictReader(source_file))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalise_archive_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def test_required_phase0_documents_exist_and_are_not_empty() -> None:
    for document in PHASE0_DOCS:
        assert document.is_file(), f"missing Phase 0 document: {document.relative_to(ROOT)}"
        assert document.stat().st_size > 0, f"empty Phase 0 document: {document.relative_to(ROOT)}"


def test_source_registry_covers_and_hashes_the_21_file_audit_baseline() -> None:
    rows = _source_rows()

    assert len(rows) == 21
    assert len({row["source_id"] for row in rows}) == 21
    assert len({row["relative_path"] for row in rows}) == 21
    assert sum(row["source_id"].startswith(ENGINEERING_PREFIXES) for row in rows) == 18
    assert {row["source_id"] for row in rows if row["source_id"].startswith("SRC-REPO-")} == {
        "SRC-REPO-001",
        "SRC-REPO-002",
        "SRC-REPO-003",
    }

    for row in rows:
        source_path = ROOT / row["relative_path"]
        assert source_path.is_file(), f"missing source: {row['relative_path']}"
        assert source_path.stat().st_size == int(row["byte_size"]), row["source_id"]
        assert _digest(source_path) == row["sha256"], row["source_id"]
        assert row["verification_status"] != "VERIFIED"


def test_zip_snapshot_is_a_byte_for_byte_copy_of_all_18_engineering_sources() -> None:
    rows = _source_rows()
    engineering_rows = [
        row for row in rows if row["source_id"].startswith(ENGINEERING_PREFIXES)
    ]
    archive_row = next(row for row in rows if row["source_id"] == "SRC-REPO-003")

    expected = {
        _normalise_archive_path(row["relative_path"]): row for row in engineering_rows
    }
    with zipfile.ZipFile(ROOT / archive_row["relative_path"]) as archive:
        members = {
            _normalise_archive_path(name): name
            for name in archive.namelist()
            if not name.endswith(("/", "\\"))
        }
        assert set(members) == set(expected)
        for relative_path, member_name in members.items():
            assert hashlib.sha256(archive.read(member_name)).hexdigest() == expected[relative_path][
                "sha256"
            ]


def test_every_engineering_rule_has_valid_source_registry_links() -> None:
    matrix = RULE_MATRIX.read_text(encoding="utf-8")
    source_ids = {row["source_id"] for row in _source_rows()}

    mapping_section = matrix.split("## Rule-to-source registry", 1)[1].split(
        "## Inverter and AC-current rules", 1
    )[0]
    rule_section = matrix.split("## Inverter and AC-current rules", 1)[1].split(
        "## Conflicts and missing information", 1
    )[0]

    declared_rules = set(re.findall(rf"^\|\s*({RULE_ID_PATTERN})\s*\|", rule_section, re.MULTILINE))
    mapped_rules = set(re.findall(RULE_ID_PATTERN, mapping_section))
    linked_sources = set(re.findall(r"SRC-[A-Z]+-\d{3}", mapping_section))

    assert declared_rules
    assert mapped_rules == declared_rules
    assert linked_sources <= source_ids
    assert "`VERIFIED`" not in rule_section


def test_conflicts_and_owner_confirmation_hold_points_are_explicit() -> None:
    matrix = RULE_MATRIX.read_text(encoding="utf-8")
    assert "## Conflicts and missing information" in matrix
    assert "## Owner-confirmation checklist" in matrix
    assert matrix.count("- [ ]") >= 10

