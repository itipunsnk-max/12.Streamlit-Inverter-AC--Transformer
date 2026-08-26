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
from solar_design.models import AmpacityAssessment, CorrectionFactor
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
    correction_factors: Sequence[DecimalLike | CorrectionFactor] = (),
    source_ids: tuple[str, ...] = ("SRC-AMP-003", "SRC-AMP-004"),
    rule_status: VerificationStatus = VerificationStatus.DRAFT,
    table_id: str | None = None,
    table_conditions: str | None = None,
    cable_cross_section_mm2: DecimalLike | None = None,
) -> AmpacityAssessment:
    """Check a table ampacity after strict-temperature and sourced factor chain.

    Plain numeric factors remain supported for compatibility, but are explicitly
    marked as unsourced inputs. ``CorrectionFactor`` values carry record IDs,
    source IDs, verification status, and conditions into the decision trace.
    """

    load = require_positive(load_current_a, "load_current_a")
    table_ampacity = require_positive(table_ampacity_a, "table_ampacity_a")
    cable_csa = (
        None
        if cable_cross_section_mm2 is None
        else require_positive(cable_cross_section_mm2, "cable_cross_section_mm2")
    )
    factor_trace: list[tuple[str, str, str, str, VerificationStatus, Decimal]] = []
    factor_findings: list[Finding] = []
    all_source_ids = list(dict.fromkeys(source_ids))
    product = Decimal("1")
    for index, raw_factor in enumerate(correction_factors):
        if isinstance(raw_factor, CorrectionFactor):
            factor = raw_factor.factor
            factor_id = raw_factor.record_id
            factor_type = raw_factor.factor_type
            factor_sources = raw_factor.metadata.source_ids
            factor_status = raw_factor.metadata.verification_status
            factor_conditions = raw_factor.conditions
            if factor_status is not VerificationStatus.VERIFIED:
                factor_findings.append(
                    Finding(
                        "CORRECTION_FACTOR_NOT_VERIFIED",
                        f"Correction factor {factor_id} has status {factor_status.value}; "
                        "engineering review is required.",
                        FindingSeverity.WARNING,
                        factor_status,
                        factor_sources,
                        f"correction_factors[{index}]",
                    )
                )
        else:
            factor = require_positive(raw_factor, f"correction_factors[{index}]")
            factor_id = f"INPUT-{index + 1:02d}"
            factor_type = "unsourced_input"
            factor_sources = ()
            factor_status = VerificationStatus.UNKNOWN
            factor_conditions = ""
            factor_findings.append(
                Finding(
                    "CORRECTION_FACTOR_SOURCE_MISSING",
                    f"Correction factor {index + 1} has no source record; it is retained as "
                    "an unsourced input.",
                    FindingSeverity.WARNING,
                    factor_status,
                    (),
                    f"correction_factors[{index}]",
                )
            )
        if factor > 1:
            raise EngineeringValidationError(
                f"correction_factors[{index}]", "must not exceed 1.0", factor
            )
        product *= factor
        factor_trace.append(
            (
                factor_id,
                factor_type,
                "|".join(factor_sources),
                factor_conditions,
                factor_status,
                factor,
            )
        )
        for source_id in factor_sources:
            if source_id not in all_source_ids:
                all_source_ids.append(source_id)
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

    findings: list[Finding] = list(
        rule_status_finding("AMP-STRICT-70C", rule_status, tuple(all_source_ids))
    )
    findings.extend(factor_findings)
    if not passed:
        findings.append(
            Finding(
                "AMPACITY_BELOW_STRICT_70C_REQUIREMENT",
                "Corrected cable ampacity is below the strict 70 °C requirement.",
                FindingSeverity.BLOCKER,
                rule_status,
                tuple(all_source_ids),
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
            TraceValue("table_id", table_id),
            TraceValue("table_conditions", table_conditions),
            TraceValue("cable_cross_section", cable_csa, "mm²"),
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
                value
                for index, (
                    factor_id,
                    factor_type,
                    factor_sources,
                    conditions,
                    status,
                    factor,
                ) in enumerate(
                    factor_trace,
                    start=1,
                )
                for value in (
                    TraceValue(f"correction_factor_{index}", factor),
                    TraceValue(f"correction_factor_{index}_id", factor_id),
                    TraceValue(f"correction_factor_{index}_type", factor_type),
                    TraceValue(f"correction_factor_{index}_source_ids", factor_sources or None),
                    TraceValue(f"correction_factor_{index}_verification_status", status.value),
                    TraceValue(f"correction_factor_{index}_conditions", conditions or None),
                )
            ]
        ),
        selected_values=(TraceValue("assessment_status", status.value),),
        source_ids=tuple(all_source_ids),
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
