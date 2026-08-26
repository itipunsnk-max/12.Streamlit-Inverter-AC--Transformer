"""Phase 5 tests for transformer sizing, currents, duty, and installation bands."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from solar_design.calculations.transformer import (
    assess_transformer_installation,
    calculate_transformer_current,
    required_transformer_kva_from_load,
    required_transformer_kva_from_pv,
    size_transformer,
    standard_transformer_ratings_from_snapshot,
    transformer_specs_from_snapshot,
)
from solar_design.domain import (
    AssessmentStatus,
    EngineeringValidationError,
    PhaseConfiguration,
    TransformerDuty,
    VerificationStatus,
)
from solar_design.repositories import ReleaseRepository

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def test_500_kva_three_phase_hv_lv_currents_are_traceable() -> None:
    result = size_transformer(
        Decimal("500"),
        high_voltage_v=Decimal("22000"),
        low_voltage_v=Decimal("400"),
        installation_type="YARD",
    )

    assert result.status is AssessmentStatus.PASS
    assert result.selected_rating_per_unit_kva == Decimal("500")
    assert result.high_voltage_current_per_unit_a is not None
    assert result.low_voltage_current_per_unit_a is not None
    assert result.high_voltage_current_per_unit_a.quantize(Decimal("0.01")) == Decimal("13.12")
    assert result.low_voltage_current_per_unit_a.quantize(Decimal("0.01")) == Decimal("721.69")
    assert result.installation_status is AssessmentStatus.PASS
    assert result.installation_assessment is not None
    assert result.installation_assessment.rule_id == "YARD-001"
    assert any(
        item.verification_status is VerificationStatus.REQUIRES_UTILITY_APPROVAL
        for item in result.installation_assessment.findings
    )


def test_load_and_pv_sizing_keep_decimal_formula_inputs_explicit() -> None:
    load_required = required_transformer_kva_from_load(
        Decimal("500"),
        demand_factor=Decimal("0.8"),
        power_factor=Decimal("0.9"),
        spare_percent=Decimal("10"),
        derating_factor=Decimal("0.95"),
    )
    pv_required = required_transformer_kva_from_pv(
        Decimal("500"),
        power_factor=Decimal("0.95"),
        design_margin_percent=Decimal("10"),
        derating_factor=Decimal("0.9"),
    )

    assert load_required.quantize(Decimal("0.01")) == Decimal("514.62")
    assert pv_required.quantize(Decimal("0.01")) == Decimal("643.27")


@pytest.mark.parametrize(
    ("required", "expected"),
    (("30", "30"), ("30.01", "50"), ("3000", "3000")),
)
def test_standard_rating_boundaries_select_smallest_supplied_rating(
    required: str,
    expected: str,
) -> None:
    result = size_transformer(Decimal(required))

    assert result.status is AssessmentStatus.PASS
    assert result.selected_rating_per_unit_kva == Decimal(expected)


def test_3001_kva_is_out_of_supplied_standard_rating_range() -> None:
    result = size_transformer(Decimal("3001"))

    assert result.status is AssessmentStatus.MISSING
    assert result.selected_rating_per_unit_kva is None
    assert result.installation_status is AssessmentStatus.NOT_ASSESSED
    assert any(item.code == "TRANSFORMER_RATING_OUT_OF_RANGE" for item in result.findings)


def test_equal_load_sharing_uses_all_units_and_n_minus_one_uses_one_less_unit() -> None:
    equal = size_transformer(
        Decimal("1000"),
        transformer_count=2,
        duty=TransformerDuty.EQUAL_SHARING,
        installation_type="YARD",
    )
    n_minus_one = size_transformer(
        Decimal("1000"),
        transformer_count=2,
        duty=TransformerDuty.N_MINUS_ONE,
        installation_type="YARD",
    )

    assert equal.required_per_unit_kva == Decimal("500")
    assert equal.selected_rating_per_unit_kva == Decimal("500")
    assert equal.normal_utilization_percent == Decimal("100")
    assert equal.contingency_utilization_percent is None
    assert equal.installation_assessment is not None
    assert equal.installation_assessment.rule_id == "YARD-004"

    assert n_minus_one.required_per_unit_kva == Decimal("1000")
    assert n_minus_one.selected_rating_per_unit_kva == Decimal("1000")
    assert n_minus_one.normal_utilization_percent == Decimal("50")
    assert n_minus_one.contingency_utilization_percent == Decimal("100")
    assert n_minus_one.installation_assessment is not None
    assert n_minus_one.installation_assessment.rule_id == "YARD-005"


@pytest.mark.parametrize("rating", ("800", "2500", "3000"))
def test_unsupported_yard_bands_are_not_interpolated(rating: str) -> None:
    assessment = assess_transformer_installation(
        Decimal(rating),
        transformer_count=1,
        installation_type="YARD",
    )

    assert assessment.status is AssessmentStatus.NOT_ASSESSED
    assert assessment.rule_id is None
    assert any(item.code == "INSTALLATION_BAND_UNSUPPORTED" for item in assessment.findings)


def test_unsupported_installation_type_does_not_create_a_pea_rule() -> None:
    result = size_transformer(
        Decimal("500"),
        installation_type="POLE_MOUNTED",
    )

    assert result.status is AssessmentStatus.PASS
    assert result.installation_status is AssessmentStatus.NOT_ASSESSED
    assert result.installation_assessment is not None
    assert result.installation_assessment.rule_id is None
    assert any(item.code == "INSTALLATION_TYPE_UNSUPPORTED" for item in result.findings)


def test_release_transformer_rows_preserve_missing_product_fields_and_rating_set() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    specs = transformer_specs_from_snapshot(snapshot)
    ratings = standard_transformer_ratings_from_snapshot(snapshot)

    assert len(specs) == 17
    assert specs[0].high_voltage_v is None
    assert specs[0].low_voltage_v is None
    assert ratings[0] == Decimal("30")
    assert ratings[-1] == Decimal("3000")
    assert Decimal("800") in ratings
    assert Decimal("2500") in ratings


def test_single_phase_current_is_not_guessed() -> None:
    with pytest.raises(EngineeringValidationError, match="single-phase"):
        calculate_transformer_current(
            Decimal("500"),
            Decimal("400"),
            phases=PhaseConfiguration.SINGLE_PHASE,
        )
