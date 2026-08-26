"""Pure functions implementing the auditable strict 70 °C method."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from solar_design.calculations._support import rule_status_finding, stable_decision_id
from solar_design.domain import (
    AssessmentStatus,
    DecisionRecord,
    Finding,
    FindingSeverity,
    TraceValue,
    VerificationStatus,
)
from solar_design.models import AmpacityAssessment
from solar_design.rules import RULES
from solar_design.validation import DecimalLike, EngineeringValidationError, require_positive


def strict_70c_required_ampacity(
    load_current_a: DecimalLike,
    *,
    ambient_temperature_c: DecimalLike = Decimal("40"),
    cable_temperature_rating_c: DecimalLike = Decimal("90"),
    terminal_temperature_limit_c: DecimalLike = Decimal("70"),
) -> Decimal:
    """Return table ampacity needed to hold the conductor at the limit.

    ``I_required = I_load / sqrt((limit - ambient) / (rating - ambient))``
    """

    load = require_positive(load_current_a, "load_current_a")
    ambient = Decimal(str(ambient_temperature_c))
    rating = Decimal(str(cable_temperature_rating_c))
    limit = Decimal(str(terminal_temperature_limit_c))
    if not all(value.is_finite() for value in (ambient, rating, limit)):
        raise EngineeringValidationError("temperature", "all temperatures must be finite")
    if not ambient < limit <= rating:
        raise EngineeringValidationError(
            "temperature",
            "temperature order must satisfy ambient < terminal limit <= cable rating",
            (ambient, limit, rating),
        )
    ratio = (limit - ambient) / (rating - ambient)
    return load / ratio.sqrt()


def check_70c_ampacity(
    load_current_a: DecimalLike,
    table_ampacity_a: DecimalLike,
    *,
    ambient_temperature_c: DecimalLike = Decimal("40"),
    cable_temperature_rating_c: DecimalLike = Decimal("90"),
    terminal_temperature_limit_c: DecimalLike = Decimal("70"),
    correction_factors: Sequence[DecimalLike] = (),
    source_ids: tuple[str, ...] = ("SRC-70C-SLIDES",),
    rule_status: VerificationStatus = VerificationStatus.DRAFT,
) -> AmpacityAssessment:
    """Check a table ampacity after strict-temperature and correction factors."""

    load = require_positive(load_current_a, "load_current_a")
    table_ampacity = require_positive(table_ampacity_a, "table_ampacity_a")
    factors: list[Decimal] = []
    product = Decimal("1")
    for index, raw_factor in enumerate(correction_factors):
        factor = require_positive(raw_factor, f"correction_factors[{index}]")
        if factor > 1:
            raise EngineeringValidationError(
                f"correction_factors[{index}]", "must not exceed 1.0", raw_factor
            )
        factors.append(factor)
        product *= factor
    strict_required = strict_70c_required_ampacity(
        load,
        ambient_temperature_c=ambient_temperature_c,
        cable_temperature_rating_c=cable_temperature_rating_c,
        terminal_temperature_limit_c=terminal_temperature_limit_c,
    )
    corrected_required = strict_required / product
    available_corrected = table_ampacity * product
    passed = available_corrected >= strict_required
    status = AssessmentStatus.PASS if passed else AssessmentStatus.FAIL

    ambient = Decimal(str(ambient_temperature_c))
    rating = Decimal(str(cable_temperature_rating_c))
    effective_table = available_corrected
    estimated_temperature = ambient + (rating - ambient) * (load / effective_table) ** 2

    findings: list[Finding] = list(rule_status_finding("AMP-STRICT-70C", rule_status, source_ids))
    if not passed:
        findings.append(
            Finding(
                "AMPACITY_BELOW_STRICT_70C_REQUIREMENT",
                "Corrected cable ampacity is below the strict 70 °C requirement.",
                FindingSeverity.BLOCKER,
                rule_status,
                source_ids,
                "table_ampacity_a",
            )
        )
    decision = DecisionRecord(
        stable_decision_id("AMP-STRICT-70C", load, table_ampacity, product),
        "ampacity",
        "AMP-STRICT-70C",
        RULES.get("AMP-STRICT-70C").version,
        rule_status,
        (
            TraceValue("load_current", load, "A"),
            TraceValue("table_ampacity", table_ampacity, "A"),
            TraceValue("ambient_temperature", ambient, "°C"),
            TraceValue("cable_temperature_rating", Decimal(str(cable_temperature_rating_c)), "°C"),
            TraceValue(
                "terminal_temperature_limit", Decimal(str(terminal_temperature_limit_c)), "°C"
            ),
        ),
        calculated_values=(
            TraceValue("strict_required_ampacity", strict_required, "A"),
            TraceValue("corrected_required_table_ampacity", corrected_required, "A"),
            TraceValue("available_corrected_ampacity", available_corrected, "A"),
            TraceValue("estimated_conductor_temperature", estimated_temperature, "°C"),
        ),
        intermediate_values=tuple(
            [TraceValue("correction_factor_product", product)]
            + [
                TraceValue(f"correction_factor_{index + 1}", factor)
                for index, factor in enumerate(factors)
            ]
        ),
        selected_values=(TraceValue("assessment_status", status.value),),
        source_ids=source_ids,
        findings=tuple(findings),
    )
    return AmpacityAssessment(
        status,
        load,
        strict_required,
        corrected_required,
        available_corrected,
        product,
        estimated_temperature,
        tuple(findings),
        decision,
    )
