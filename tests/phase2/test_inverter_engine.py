"""Phase 2 tests for inverter catalogue adaptation, selection, and AC current traceability."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from solar_design.calculations.inverter import (
    calculate_ac_circuits,
    inverter_specs_from_snapshot,
    select_inverters,
)
from solar_design.domain import (
    DecisionRecord,
    EngineeringValidationError,
    PhaseConfiguration,
    TraceValue,
    VerificationStatus,
)
from solar_design.models import InverterSpec, RecordMetadata
from solar_design.repositories import ReleaseRepository

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def _metadata(
    record_id: str,
    status: VerificationStatus = VerificationStatus.DRAFT,
) -> RecordMetadata:
    return RecordMetadata(
        record_id=record_id,
        revision="1",
        verification_status=status,
        source_id="SRC-INV-TEST",
        effective_from=date(2026, 1, 1),
    )


def _inverter(
    record_id: str,
    ac_power_kw: str,
    maximum_dc_power_kwp: str | None,
    dc_ac_ratio: str | None,
    *,
    ac_voltage_v: str | None = "400",
    phases: PhaseConfiguration | None = PhaseConfiguration.THREE_PHASE,
    maximum_output_current_a: str | None = None,
) -> InverterSpec:
    return InverterSpec(
        metadata=_metadata(record_id),
        manufacturer="Test Manufacturer",
        model=record_id,
        ac_power_kw=Decimal(ac_power_kw),
        ac_voltage_v=Decimal(ac_voltage_v) if ac_voltage_v is not None else None,
        phases=phases,
        maximum_output_current_a=(
            Decimal(maximum_output_current_a)
            if maximum_output_current_a is not None
            else None
        ),
        maximum_dc_power_kwp=(
            Decimal(maximum_dc_power_kwp) if maximum_dc_power_kwp is not None else None
        ),
        dc_ac_ratio=Decimal(dc_ac_ratio) if dc_ac_ratio is not None else None,
    )


def _trace_value(decision: DecisionRecord, name: str) -> TraceValue:
    return next(item for item in decision.calculated_values if item.name == name)


def test_selection_uses_the_selected_model_ratio_and_does_not_apply_global_1_40() -> None:
    catalogue = (
        _inverter("INV-36", "36", "50.4", "1.40"),
        _inverter("INV-50", "50", "62.5", "1.25"),
    )

    result = select_inverters(Decimal("60"), catalogue)

    assert result.selected_model_id == "INV-50"
    assert result.quantity == 1
    assert result.selected_model_dc_ac_ratio == Decimal("1.25")
    assert result.dc_ac_ratio == Decimal("1.2")
    assert _trace_value(result.decision, "model_dc_ac_ratio").value == Decimal("1.25")
    assert _trace_value(result.decision, "requested_to_installed_ac_ratio").value == Decimal("1.2")
    assert any(item.code == "INVERTER_DC_AC_RATIO_MODEL_SPECIFIC" for item in result.findings)


def test_eligibility_records_allowed_set_and_voltage_rejection_reasons() -> None:
    catalogue = (
        _inverter("INV-36", "36", "50.4", "1.40", ac_voltage_v="400"),
        _inverter("INV-50", "50", "70", "1.40", ac_voltage_v="415"),
    )

    result = select_inverters(
        Decimal("40"),
        catalogue,
        required_ac_voltage_v=Decimal("400"),
        allowed_model_ids=frozenset({"INV-50"}),
    )

    assert result.selected_model_id is None
    candidates = {candidate.candidate_id: candidate for candidate in result.decision.candidates}
    assert candidates["INV-36"].accepted is False
    assert "model is outside the allowed set" in candidates["INV-36"].reasons
    assert candidates["INV-50"].accepted is False
    assert "AC voltage does not match the system basis" in candidates["INV-50"].reasons


def test_missing_dc_limit_is_not_eligible_and_is_never_inferred() -> None:
    sg350 = _inverter("INV-SG350HX-20", "350", None, None)

    result = select_inverters(Decimal("100"), (sg350,))

    assert result.selected_model_id is None
    assert result.total_dc_capacity_kwp is None
    assert result.selected_model_dc_ac_ratio is None
    candidate = result.decision.candidates[0]
    assert candidate.accepted is False
    assert "model has no sourced maximum DC power" in candidate.reasons
    assert not any(item.code == "INVERTER_DC_AC_RATIO_INFERRED" for item in result.findings)


def test_override_requires_reason_and_can_explicitly_select_unknown_dc_limit() -> None:
    sg350 = _inverter("INV-SG350HX-20", "350", None, None)

    with pytest.raises(EngineeringValidationError):
        select_inverters(Decimal("100"), (sg350,), override_model_id=sg350.record_id)

    result = select_inverters(
        Decimal("100"),
        (sg350,),
        override_model_id=sg350.record_id,
        override_reason="Owner requested budgetary placeholder pending datasheet confirmation.",
    )

    assert result.selected_model_id == sg350.record_id
    assert result.quantity == 1
    assert result.total_dc_capacity_kwp is None
    assert result.decision.verification_status is VerificationStatus.USER_OVERRIDE
    assert result.decision.override_reason
    assert any(item.code == "INVERTER_DC_CAPACITY_UNKNOWN" for item in result.findings)


@pytest.mark.parametrize(
    ("record_id", "rated_kw", "voltage_v", "maximum_current_a", "mppt_count"),
    (
        ("INV-SUNGROW-SG36CX-P2", "36", "400", "60.2", 4),
        ("INV-SUNGROW-SG40CX-P2", "40", "400", "66.9", 4),
        ("INV-SUNGROW-SG50CX-P2", "50", "400", "83.6", 4),
        ("INV-SUNGROW-SG125CX-P2", "125", "400", "181.1", 12),
        ("INV-SUNGROW-SG150CX", "150", "400", "240.6", 7),
        ("INV-SUNGROW-SG350HX-20", "320", "800", "254", 6),
    ),
)
def test_reference_catalogue_preserves_official_sungrow_ac_fields(
    record_id: str,
    rated_kw: str,
    voltage_v: str,
    maximum_current_a: str,
    mppt_count: int,
) -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    catalogue = inverter_specs_from_snapshot(snapshot)

    inverter = next(item for item in catalogue if item.record_id == record_id)

    assert inverter.ac_power_kw == Decimal(rated_kw)
    assert inverter.ac_voltage_v == Decimal(voltage_v)
    assert inverter.maximum_output_current_a == Decimal(maximum_current_a)
    assert inverter.mppt_count == mppt_count
    assert inverter.phases is PhaseConfiguration.THREE_PHASE


def test_reference_catalogue_adapter_uses_official_sg350_rated_conditions() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()

    catalogue = inverter_specs_from_snapshot(snapshot)
    sg350 = next(item for item in catalogue if item.record_id == "INV-SUNGROW-SG350HX-20")

    assert sg350.ac_power_kw == Decimal("320")
    assert sg350.ac_apparent_power_kva == Decimal("352")
    assert sg350.maximum_dc_power_kwp is None
    assert sg350.dc_ac_ratio is None
    assert sg350.ac_voltage_v == Decimal("800")
    assert sg350.phases is PhaseConfiguration.THREE_PHASE
    assert sg350.maximum_output_current_a == Decimal("254")
    assert sg350.maximum_dc_input_current_a == Decimal("450")
    assert sg350.maximum_input_current_per_mppt_a == Decimal("75")
    assert sg350.max_short_circuit_current_per_mppt_a == Decimal("125")
    assert sg350.dc_max_voltage_v == Decimal("1500")
    assert sg350.startup_voltage_v == Decimal("550")
    assert sg350.mppt_min_voltage_v == Decimal("500")
    assert sg350.mppt_max_voltage_v == Decimal("1500")
    assert sg350.inputs_per_mppt == 5
    assert sg350.ac_connection == "3-PE"


def test_ac_current_prefers_manufacturer_maximum_and_records_trace() -> None:
    inverter = _inverter(
        "INV-50",
        "50",
        "70",
        "1.40",
        maximum_output_current_a="75",
    )
    selection = select_inverters(Decimal("50"), (inverter,))

    circuits = calculate_ac_circuits(selection, (inverter,))

    assert len(circuits) == 1
    assert circuits[0].design_current_a == Decimal("75")
    assert circuits[0].current_basis == "manufacturer_maximum_output_current"
    assert _trace_value(circuits[0].decision, "design_current").value == Decimal("75")
    assert circuits[0].decision.source_ids == ("SRC-INV-TEST",)


def test_ac_current_fallback_is_calculated_when_required_inputs_exist() -> None:
    inverter = _inverter("INV-36", "36", "50.4", "1.40")
    selection = select_inverters(Decimal("40"), (inverter,))

    circuit = calculate_ac_circuits(selection, (inverter,))[0]

    assert circuit.current_basis == "calculated_fallback"
    assert circuit.design_current_a is not None
    assert circuit.design_current_a == pytest.approx(
        Decimal("51.96152422706632"), rel=Decimal("1e-12")
    )
    assert any(item.code == "INVERTER_CURRENT_FALLBACK" for item in circuit.findings)


def test_ac_current_is_not_assessed_when_catalogue_voltage_or_phase_is_missing() -> None:
    inverter = _inverter(
        "INV-SG350HX-20",
        "350",
        None,
        None,
        ac_voltage_v=None,
        phases=None,
    )
    selection = select_inverters(
        Decimal("100"),
        (inverter,),
        override_model_id=inverter.record_id,
        override_reason="Budgetary placeholder pending manufacturer data.",
    )

    circuit = calculate_ac_circuits(selection, (inverter,))[0]

    assert circuit.design_current_a is None
    assert circuit.current_basis == "not_assessed_missing_voltage_or_phase"
    assert circuit.decision.verification_status is VerificationStatus.UNKNOWN
    assert any(item.code == "INVERTER_CURRENT_NOT_ASSESSED" for item in circuit.findings)
