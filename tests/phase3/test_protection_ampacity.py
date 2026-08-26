"""Phase 3 tests for protection assessment and strict 70 °C ampacity."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from solar_design.calculations.ampacity import (
    check_70c_ampacity,
    grouping_factors_from_snapshot,
    select_grouping_factor,
)
from solar_design.calculations.protection import (
    protection_candidates_from_snapshot,
    select_protection,
)
from solar_design.domain import (
    AssessmentStatus,
    DecisionRecord,
    FindingSeverity,
    TraceValue,
    VerificationStatus,
)
from solar_design.models import CorrectionFactor, RecordMetadata
from solar_design.repositories import ReleaseRepository

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def _metadata(
    record_id: str,
    source_id: str,
    status: VerificationStatus = VerificationStatus.DRAFT,
) -> RecordMetadata:
    return RecordMetadata(
        record_id=record_id,
        revision="1",
        verification_status=status,
        source_id=source_id,
        effective_from=date(2026, 1, 1),
    )


def _trace_value(decision: DecisionRecord, name: str) -> TraceValue:
    return next(item for item in decision.intermediate_values if item.name == name)


def test_strict_70c_100_ampere_requires_129_10_ampere_table_rating() -> None:
    result = check_70c_ampacity(
        Decimal("100"),
        Decimal("131"),
        table_id="TABLE-5-27",
        table_conditions="Group 2, three loaded 1-core CV conductors, 40 °C ambient",
        cable_cross_section_mm2=Decimal("35"),
        source_ids=("SRC-AMP-003", "SRC-AMP-004"),
    )

    assert result.strict_70c_required_ampacity_a.quantize(Decimal("0.01")) == Decimal("129.10")
    assert result.status is AssessmentStatus.PASS
    inputs = {item.name: item.value for item in result.decision.inputs}
    assert inputs["table_id"] == "TABLE-5-27"
    assert inputs["cable_cross_section"] == Decimal("35")
    assert result.decision.source_ids == ("SRC-AMP-003", "SRC-AMP-004")


@pytest.mark.parametrize(
    ("csa", "table_ampacity", "expected_status"),
    (
        ("25", "106", AssessmentStatus.FAIL),
        ("35", "131", AssessmentStatus.PASS),
    ),
)
def test_group_2_cv_table_boundaries_are_25_fail_and_35_pass(
    csa: str,
    table_ampacity: str,
    expected_status: AssessmentStatus,
) -> None:
    result = check_70c_ampacity(
        Decimal("100"),
        Decimal(table_ampacity),
        table_id="TABLE-5-27",
        table_conditions="Group 2, three loaded 1-core CV conductors",
        cable_cross_section_mm2=Decimal(csa),
        source_ids=("SRC-AMP-003", "SRC-AMP-004"),
    )

    assert result.status is expected_status
    if expected_status is AssessmentStatus.FAIL:
        assert any(item.code == "AMPACITY_BELOW_STRICT_70C_REQUIREMENT" for item in result.findings)


def test_correction_factor_chain_preserves_values_sources_status_and_conditions() -> None:
    grouping = CorrectionFactor(
        metadata=_metadata("GRP-2", "SRC-WIR-004", VerificationStatus.DRAFT),
        factor_type="grouping",
        factor=Decimal("0.80"),
        label="SAME_RACEWAY:2",
        conditions="Two circuit groups in the same raceway",
    )
    ambient = CorrectionFactor(
        metadata=_metadata("AMB-40", "SRC-AMP-003", VerificationStatus.ASSUMPTION),
        factor_type="ambient",
        factor=Decimal("0.90"),
        label="ambient-40C",
        conditions="Ambient correction pending approved table",
    )

    result = check_70c_ampacity(
        Decimal("100"),
        Decimal("200"),
        correction_factors=(grouping, ambient),
        source_ids=("SRC-AMP-004",),
        table_id="TABLE-5-27",
        table_conditions="Worked example conditions",
    )

    assert result.correction_factor_product == Decimal("0.7200")
    assert result.corrected_required_table_ampacity_a == (
        result.strict_70c_required_ampacity_a / Decimal("0.7200")
    )
    assert result.decision.source_ids == ("SRC-AMP-004", "SRC-WIR-004", "SRC-AMP-003")
    assert _trace_value(result.decision, "correction_factor_1_id").value == "GRP-2"
    assert _trace_value(result.decision, "correction_factor_1_source_ids").value == "SRC-WIR-004"
    assert (
        _trace_value(result.decision, "correction_factor_2_verification_status").value
        == "ASSUMPTION"
    )
    assert any(item.code == "CORRECTION_FACTOR_NOT_VERIFIED" for item in result.findings)


def test_grouping_factor_lookup_honors_inclusive_range_boundaries() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    factors = grouping_factors_from_snapshot(snapshot)
    expected = {
        1: "1.00",
        2: "0.80",
        3: "0.70",
        9: "0.50",
        10: "0.45",
        12: "0.45",
        13: "0.41",
        16: "0.41",
        17: "0.38",
        20: "0.38",
    }

    for group_count, expected_factor in expected.items():
        selected = select_grouping_factor(group_count, factors)
        assert selected.factor == Decimal(expected_factor)
        assert selected.metadata.source_id == "SRC-WIR-004"

    with pytest.raises(ValueError):
        select_grouping_factor(0, factors)
    with pytest.raises(ValueError):
        select_grouping_factor(21, factors)


def test_draft_breaker_catalogue_is_traceable_but_not_assessed_or_selected() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    candidates = protection_candidates_from_snapshot(snapshot)

    result = select_protection(Decimal("100"), candidates)

    assert result.status is AssessmentStatus.NOT_ASSESSED
    assert result.selected_breaker_id is None
    assert len(result.decision.candidates) == 4
    assert all(not item.accepted for item in result.decision.candidates)
    draft_findings = [
        item for item in result.findings if item.code == "PROTECTION_CANDIDATE_NOT_VERIFIED"
    ]
    assert len(draft_findings) == 4
    assert all(item.severity is FindingSeverity.WARNING for item in draft_findings)
    assert all(item.verification_status is VerificationStatus.DRAFT for item in draft_findings)
    assert result.decision.source_ids == ("SRC-INV-002",)
    assert any(item.code == "PROTECTION_NOT_ASSESSED" for item in result.findings)


def test_protection_without_catalogue_still_returns_not_assessed_warning() -> None:
    result = select_protection(Decimal("100"))

    assert result.status is AssessmentStatus.NOT_ASSESSED
    assert result.selected_breaker_id is None
    assert result.findings[0].code == "PROTECTION_NOT_ASSESSED"
    assert result.findings[0].severity is FindingSeverity.WARNING
