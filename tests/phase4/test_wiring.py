"""Phase 4 regression tests for cable, PE, and conduit behavior."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from solar_design.calculations.wiring import (
    allocate_cable_conduits,
    allocate_conduits,
    allocate_parallel_circuit_conduits,
    ampacity_records_from_snapshot,
    cable_specs_from_snapshot,
    conduit_specs_from_snapshot,
    select_cable,
    select_pe_conductor,
)
from solar_design.domain import (
    AssessmentStatus,
    EngineeringValidationError,
    FindingSeverity,
    VerificationStatus,
)
from solar_design.models import (
    AmpacityRecord,
    CableSpec,
    ConduitSpec,
    PESelectionRule,
    RecordMetadata,
)
from solar_design.repositories import ReleaseRepository

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def _metadata(
    record_id: str,
    source_id: str = "SRC-WIR-003",
    status: VerificationStatus = VerificationStatus.DRAFT,
) -> RecordMetadata:
    return RecordMetadata(
        record_id=record_id,
        revision="1",
        verification_status=status,
        source_id=source_id,
        effective_from=date(2026, 1, 1),
    )


def _cable(
    record_id: str,
    csa: str,
    od: str | None = "20",
) -> CableSpec:
    return CableSpec(
        metadata=_metadata(record_id),
        manufacturer="Test Cable",
        model=f"CV {csa} mm2",
        family="CV",
        material="CU",
        insulation="XLPE",
        voltage_class_v=Decimal("1000"),
        cores=1,
        cross_section_mm2=Decimal(csa),
        outside_diameter_mm=Decimal(od) if od is not None else None,
        temperature_rating_c=Decimal("90"),
    )


def _conduit(internal_diameter: str = "54") -> ConduitSpec:
    return ConduitSpec(
        metadata=_metadata("CON-TEST"),
        conduit_type="IMC",
        trade_size="TEST",
        internal_diameter_mm=Decimal(internal_diameter),
        standard="TEST",
    )


def test_release_adapters_preserve_broken_od_and_link_ampacity_by_explicit_identity() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    cables = cable_specs_from_snapshot(snapshot)
    linked_ampacity = ampacity_records_from_snapshot(snapshot, cables)

    pv = next(item for item in cables if item.record_id.endswith("1C-004"))
    assert pv.outside_diameter_mm is None
    assert any(item.cable_id.endswith("1C-035") for item in linked_ampacity)

    result = allocate_cable_conduits((pv,), conduit_specs_from_snapshot(snapshot))
    assert result.status is AssessmentStatus.MISSING
    assert any(item.code == "CABLE_OD_MISSING" for item in result.findings)
    assert all(item.severity is FindingSeverity.REVIEW for item in result.findings)


def test_exact_pe_lookup_does_not_extrapolate_missing_size() -> None:
    rules = (
        PESelectionRule(
            metadata=_metadata("PE-35-25", "SRC-WIR-002"),
            phase_cross_section_mm2=Decimal("35"),
            pe_cross_section_mm2=Decimal("25"),
        ),
    )

    result = select_pe_conductor(Decimal("36"), rules)

    assert result.status is AssessmentStatus.MISSING
    assert result.pe_cross_section_mm2 is None
    assert any(item.code == "PE_RULE_MISSING" for item in result.findings)
    assert all(item.severity is FindingSeverity.REVIEW for item in result.findings)


def test_missing_pe_value_is_review_not_a_pass() -> None:
    rule = PESelectionRule(
        metadata=_metadata("PE-35-MISSING", "SRC-WIR-002"),
        phase_cross_section_mm2=Decimal("35"),
        pe_cross_section_mm2=None,
    )

    result = select_pe_conductor(Decimal("35"), (rule,))

    assert result.status is AssessmentStatus.MISSING
    assert result.pe_cross_section_mm2 is None
    assert result.findings[0].code == "PE_SIZE_MISSING"
    assert result.findings[0].severity is FindingSeverity.REVIEW


def test_model_csa_mismatch_is_a_hard_block() -> None:
    with pytest.raises(EngineeringValidationError, match="model CSA"):
        CableSpec(
            metadata=_metadata("CAB-MISMATCH"),
            manufacturer="Test Cable",
            model="CV 35 mm2",
            family="CV",
            material="CU",
            insulation="XLPE",
            voltage_class_v=Decimal("1000"),
            cores=1,
            cross_section_mm2=Decimal("25"),
            outside_diameter_mm=Decimal("12"),
            temperature_rating_c=Decimal("90"),
        )


def test_broken_reference_and_blank_rows_never_return_pass() -> None:
    conduit = (_conduit(),)

    cases = (
        (("#REF!",), "CABLE_OD_MISSING"),
        (("",), "CABLE_OD_MISSING"),
        ((), "BLANK_CABLE_ROW"),
    )
    for values, expected_code in cases:
        result = allocate_conduits(values, conduit)
        assert result.status is AssessmentStatus.MISSING
        assert any(item.code == expected_code for item in result.findings)
        assert all(item.severity is FindingSeverity.REVIEW for item in result.findings)


def test_parallel_allocation_assigns_whole_cables_and_applies_count_specific_fill() -> None:
    result = allocate_conduits(("20", "20", "20"), (_conduit(),), max_conduits=2)

    assert result.status is AssessmentStatus.PASS
    assert result.conduit_id == "CON-TEST"
    assert len(result.runs) == 2
    assert sum(run.cable_count for run in result.runs) == 3
    assert sorted(run.cable_count for run in result.runs) == [1, 2]
    assert all(run.actual_fill_percent <= run.permitted_fill_percent for run in result.runs)
    assert all(
        len(run.cable_indices) == run.cable_count
        and all(isinstance(index, int) for index in run.cable_indices)
        for run in result.runs
    )


def test_parallel_circuit_allocation_keeps_each_full_3npe_set_in_one_conduit() -> None:
    phase = _cable("CAB-PHASE-35", "35", "13")
    pe = _cable("CAB-PE-25", "25", "9.7")

    result = allocate_parallel_circuit_conduits(
        phase,
        pe,
        (_conduit("54"),),
        phase_conductors_per_run=3,
        neutral_conductors_per_run=1,
        parallel_runs=2,
    )

    assert result.status is AssessmentStatus.PASS
    assert len(result.runs) == 2
    assert all(run.cable_count == 5 for run in result.runs)
    assert all(run.permitted_fill_percent == Decimal("40") for run in result.runs)
    assert result.runs[0].cable_indices == (0, 1, 2, 3, 4)
    assert result.runs[1].cable_indices == (5, 6, 7, 8, 9)
    assert all(run.actual_fill_percent <= Decimal("40") for run in result.runs)


def test_cable_selection_uses_ampacity_link_and_keeps_parallel_count_explicit() -> None:
    cable = _cable("CAB-35", "35")
    ampacity = AmpacityRecord(
        metadata=_metadata("AMP-35", "SRC-AMP-004"),
        cable_id=cable.record_id,
        installation_method="UNSPECIFIED",
        current_carrying_conductors=3,
        reference_ambient_c=Decimal("40"),
        ampacity_a=Decimal("131"),
    )

    result = select_cable(
        Decimal("200"),
        (cable,),
        (ampacity,),
        installation_method="UNSPECIFIED",
        current_carrying_conductors=3,
        max_parallel_runs=2,
    )

    assert result.status is AssessmentStatus.PASS
    assert result.parallel_runs == 2
    assert result.total_ampacity_a == Decimal("262")
