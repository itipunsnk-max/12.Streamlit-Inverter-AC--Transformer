"""Pure transformer sizing functions for budgetary design."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from solar_design.calculations._support import (
    HUNDRED,
    SQRT_THREE,
    rule_status_finding,
    stable_decision_id,
)
from solar_design.domain import (
    AssessmentStatus,
    CandidateRecord,
    DecisionRecord,
    EngineeringValidationError,
    Finding,
    FindingSeverity,
    PhaseConfiguration,
    TraceValue,
    TransformerDuty,
    VerificationStatus,
)
from solar_design.models import TransformerSelection
from solar_design.rules import DEFAULT_STANDARD_TRANSFORMER_RATINGS_KVA, RULES
from solar_design.validation import (
    DecimalLike,
    require_between_zero_and_one,
    require_non_negative,
    require_positive,
)


def required_transformer_kva_from_load(
    load_kw: DecimalLike,
    *,
    demand_factor: DecimalLike = Decimal("1"),
    power_factor: DecimalLike = Decimal("1"),
    spare_percent: DecimalLike = Decimal("0"),
    derating_factor: DecimalLike = Decimal("1"),
) -> Decimal:
    """Apply ``load × demand / PF × (1 + spare) / derating``."""

    load = require_positive(load_kw, "load_kw")
    demand = require_between_zero_and_one(demand_factor, "demand_factor")
    pf = require_between_zero_and_one(power_factor, "power_factor")
    spare = require_non_negative(spare_percent, "spare_percent")
    derating = require_between_zero_and_one(derating_factor, "derating_factor")
    return load * demand / pf * (Decimal("1") + spare / HUNDRED) / derating


def required_transformer_kva_from_pv(
    total_inverter_ac_power_kw: DecimalLike,
    *,
    power_factor: DecimalLike = Decimal("1"),
    design_margin_percent: DecimalLike = Decimal("0"),
    derating_factor: DecimalLike = Decimal("1"),
) -> Decimal:
    """Budgetary PV sizing assumption pending an approved utility formula."""

    power = require_positive(total_inverter_ac_power_kw, "total_inverter_ac_power_kw")
    pf = require_between_zero_and_one(power_factor, "power_factor")
    margin = require_non_negative(design_margin_percent, "design_margin_percent")
    derating = require_between_zero_and_one(derating_factor, "derating_factor")
    return power / pf * (Decimal("1") + margin / HUNDRED) / derating


def calculate_transformer_current(
    rating_kva: DecimalLike,
    voltage_v: DecimalLike,
    *,
    phases: PhaseConfiguration = PhaseConfiguration.THREE_PHASE,
) -> Decimal:
    rating = require_positive(rating_kva, "rating_kva")
    voltage = require_positive(voltage_v, "voltage_v")
    divisor = SQRT_THREE * voltage if phases is PhaseConfiguration.THREE_PHASE else voltage
    return rating * Decimal("1000") / divisor


def size_transformer(
    required_bank_kva: DecimalLike,
    *,
    standard_ratings_kva: Sequence[DecimalLike] = DEFAULT_STANDARD_TRANSFORMER_RATINGS_KVA,
    transformer_count: int = 1,
    duty: TransformerDuty = TransformerDuty.EQUAL_SHARING,
    high_voltage_v: DecimalLike = Decimal("22000"),
    low_voltage_v: DecimalLike = Decimal("400"),
    phases: PhaseConfiguration = PhaseConfiguration.THREE_PHASE,
    installation_type: str | None = None,
    sizing_rule_status: VerificationStatus = VerificationStatus.DRAFT,
    override_rating_per_unit_kva: DecimalLike | None = None,
    override_reason: str | None = None,
) -> TransformerSelection:
    """Select the smallest standard per-unit rating for equal or N-1 duty."""

    required = require_positive(required_bank_kva, "required_bank_kva")
    hv = require_positive(high_voltage_v, "high_voltage_v")
    lv = require_positive(low_voltage_v, "low_voltage_v")
    if transformer_count <= 0:
        raise EngineeringValidationError("transformer_count", "must be greater than zero")
    if duty is TransformerDuty.N_MINUS_ONE and transformer_count < 2:
        raise EngineeringValidationError(
            "transformer_count", "N-1 duty requires at least two transformers"
        )
    if override_rating_per_unit_kva is not None and (
        not override_reason or not override_reason.strip()
    ):
        raise EngineeringValidationError(
            "override_reason", "is required for a transformer rating override"
        )
    ratings = tuple(
        sorted({require_positive(item, "standard_ratings_kva") for item in standard_ratings_kva})
    )
    if not ratings and override_rating_per_unit_kva is None:
        raise EngineeringValidationError("standard_ratings_kva", "must contain at least one rating")

    available_units = (
        transformer_count if duty is TransformerDuty.EQUAL_SHARING else transformer_count - 1
    )
    required_per_unit = required / available_units
    candidates = tuple(
        CandidateRecord(
            f"{rating}-kVA",
            rating >= required_per_unit,
            () if rating >= required_per_unit else ("rating is below required per-unit capacity",),
        )
        for rating in ratings
    )
    findings: list[Finding] = list(
        rule_status_finding("TX-SIZE-LOAD", sizing_rule_status, ("SRC-TRANSFORMER-BRIEF",))
    )
    decision_status = sizing_rule_status
    selected: Decimal | None
    if override_rating_per_unit_kva is not None:
        selected = require_positive(override_rating_per_unit_kva, "override_rating_per_unit_kva")
        decision_status = VerificationStatus.USER_OVERRIDE
    else:
        selected = next((rating for rating in ratings if rating >= required_per_unit), None)

    if selected is None:
        status = AssessmentStatus.MISSING
        installed = None
        normal_utilization = None
        contingency_utilization = None
        hv_current = None
        lv_current = None
        findings.append(
            Finding(
                "TRANSFORMER_RATING_OUT_OF_RANGE",
                "Required per-unit capacity exceeds the available standard ratings.",
                FindingSeverity.BLOCKER,
                VerificationStatus.UNKNOWN,
            )
        )
    else:
        installed = selected * transformer_count
        normal_utilization = required / installed * HUNDRED
        contingency_utilization = (
            required / (selected * (transformer_count - 1)) * HUNDRED
            if duty is TransformerDuty.N_MINUS_ONE
            else None
        )
        hv_current = calculate_transformer_current(selected, hv, phases=phases)
        lv_current = calculate_transformer_current(selected, lv, phases=phases)
        if selected < required_per_unit:
            status = AssessmentStatus.FAIL
            findings.append(
                Finding(
                    "TRANSFORMER_OVERRIDE_UNDERSIZED",
                    "The overridden transformer rating is below the required per-unit capacity.",
                    FindingSeverity.BLOCKER,
                    VerificationStatus.USER_OVERRIDE,
                    field="override_rating_per_unit_kva",
                )
            )
        else:
            status = AssessmentStatus.PASS

    installation_status = AssessmentStatus.NOT_ASSESSED
    findings.append(
        Finding(
            "INSTALLATION_TYPE_NOT_ASSESSED",
            (
                "Installation eligibility is not assessed because approved "
                "PEA/MEA rules are unavailable."
                if installation_type
                else "Installation type was not supplied and approved eligibility "
                "rules are unavailable."
            ),
            FindingSeverity.WARNING,
            VerificationStatus.REQUIRES_UTILITY_APPROVAL,
            field="installation_type",
        )
    )
    decision = DecisionRecord(
        stable_decision_id("TX-SIZE", required, transformer_count, duty, selected),
        "transformer",
        "TX-SIZE-LOAD",
        RULES.get("TX-SIZE-LOAD").version,
        decision_status,
        (
            TraceValue("required_bank_capacity", required, "kVA"),
            TraceValue("transformer_count", transformer_count),
            TraceValue("duty", duty.value),
            TraceValue("high_voltage", hv, "V"),
            TraceValue("low_voltage", lv, "V"),
            TraceValue("phases", phases.value),
            TraceValue("installation_type", installation_type),
        ),
        intermediate_values=(
            TraceValue("available_units_for_duty", available_units),
            TraceValue("required_per_unit", required_per_unit, "kVA"),
        ),
        calculated_values=(
            TraceValue("installed_bank_capacity", installed, "kVA"),
            TraceValue("normal_utilization", normal_utilization, "%"),
            TraceValue("contingency_utilization", contingency_utilization, "%"),
            TraceValue("high_voltage_current_per_unit", hv_current, "A"),
            TraceValue("low_voltage_current_per_unit", lv_current, "A"),
        ),
        selected_values=(TraceValue("selected_rating_per_unit", selected, "kVA"),),
        candidates=candidates,
        source_ids=("SRC-TRANSFORMER-BRIEF",),
        findings=tuple(findings),
        override_reason=override_reason if override_rating_per_unit_kva is not None else None,
    )
    return TransformerSelection(
        status,
        duty,
        transformer_count,
        required,
        required_per_unit,
        selected,
        installed,
        normal_utilization,
        contingency_utilization,
        hv_current,
        lv_current,
        installation_status,
        tuple(findings),
        decision,
    )
