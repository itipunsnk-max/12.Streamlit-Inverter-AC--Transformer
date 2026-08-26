"""Pure inverter selection and current calculation functions."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from solar_design.calculations._support import (
    SQRT_THREE,
    ceil_decimal,
    rule_status_finding,
    stable_decision_id,
)
from solar_design.domain import (
    CandidateRecord,
    DecisionRecord,
    EngineeringValidationError,
    Finding,
    FindingSeverity,
    PhaseConfiguration,
    TraceValue,
    VerificationStatus,
)
from solar_design.models import CircuitRequirement, InverterSelection, InverterSpec
from solar_design.rules import RULES
from solar_design.validation import DecimalLike, require_between_zero_and_one, require_positive


def calculate_ac_current(
    ac_power_kw: DecimalLike,
    voltage_v: DecimalLike,
    *,
    phases: PhaseConfiguration = PhaseConfiguration.THREE_PHASE,
    power_factor: DecimalLike = Decimal("1"),
    efficiency: DecimalLike = Decimal("1"),
) -> Decimal:
    """Calculate line current from real power.

    Three phase: ``P*1000 / (sqrt(3)*V*PF*efficiency)``.
    Single phase: ``P*1000 / (V*PF*efficiency)``.
    """

    power = require_positive(ac_power_kw, "ac_power_kw")
    voltage = require_positive(voltage_v, "voltage_v")
    pf = require_between_zero_and_one(power_factor, "power_factor")
    eta = require_between_zero_and_one(efficiency, "efficiency")
    phase_factor = SQRT_THREE if phases is PhaseConfiguration.THREE_PHASE else Decimal("1")
    return power * Decimal("1000") / (phase_factor * voltage * pf * eta)


def select_inverters(
    required_dc_power_kwp: DecimalLike,
    catalogue: Sequence[InverterSpec],
    *,
    required_ac_voltage_v: DecimalLike | None = None,
    allowed_model_ids: frozenset[str] | None = None,
    override_model_id: str | None = None,
    override_reason: str | None = None,
) -> InverterSelection:
    """Select the lowest installed AC capacity that covers required DC power.

    DC capacity is model-specific catalogue data. A missing value is never
    inferred from a global DC/AC ratio. A manual model override remains usable
    for budgeting but must include a reason.
    """

    required = require_positive(required_dc_power_kwp, "required_dc_power_kwp")
    voltage = (
        None
        if required_ac_voltage_v is None
        else require_positive(required_ac_voltage_v, "required_ac_voltage_v")
    )
    if not catalogue:
        raise EngineeringValidationError("catalogue", "must contain at least one inverter")
    if override_model_id and (not override_reason or not override_reason.strip()):
        raise EngineeringValidationError(
            "override_reason", "is required when overriding inverter selection"
        )

    candidate_records: list[CandidateRecord] = []
    ranked: list[tuple[Decimal, int, str, InverterSpec]] = []
    by_id = {item.record_id: item for item in catalogue}
    if len(by_id) != len(catalogue):
        raise EngineeringValidationError("catalogue", "contains duplicate inverter record IDs")

    for item in catalogue:
        reasons: list[str] = []
        if allowed_model_ids is not None and item.record_id not in allowed_model_ids:
            reasons.append("model is outside the allowed set")
        if voltage is not None:
            if item.ac_voltage_v is None:
                reasons.append("model has no sourced AC voltage")
            elif item.ac_voltage_v != voltage:
                reasons.append("AC voltage does not match the system basis")
        maximum_dc_power = item.maximum_dc_power_kwp
        if maximum_dc_power is None:
            reasons.append("model has no sourced maximum DC power")
        if reasons:
            candidate_records.append(CandidateRecord(item.record_id, False, tuple(reasons)))
            continue
        if maximum_dc_power is None:  # narrowed by the rejection branch above
            continue
        quantity = ceil_decimal(required / maximum_dc_power)
        candidate_total_ac = item.ac_power_kw * quantity
        ranked.append((candidate_total_ac, quantity, item.record_id, item))
        candidate_records.append(CandidateRecord(item.record_id, True, ()))

    findings: list[Finding] = []
    selected: InverterSpec | None = None
    quantity = 0
    status = RULES.get("INV-DC-CAPACITY").verification_status
    selected_status = status

    if override_model_id is not None:
        selected = by_id.get(override_model_id)
        if selected is None:
            raise EngineeringValidationError(
                "override_model_id", "does not exist in catalogue", override_model_id
            )
        if voltage is not None:
            if selected.ac_voltage_v is None:
                raise EngineeringValidationError(
                    "override_model_id", "has no sourced AC voltage", override_model_id
                )
            if selected.ac_voltage_v != voltage:
                raise EngineeringValidationError(
                    "override_model_id", "has an incompatible AC voltage", override_model_id
                )
        selected_status = VerificationStatus.USER_OVERRIDE
        if selected.maximum_dc_power_kwp is None:
            quantity = 1
            findings.append(
                Finding(
                    "INVERTER_DC_CAPACITY_UNKNOWN",
                    "The overridden model has no sourced DC kWp limit; "
                    "quantity cannot be validated.",
                    FindingSeverity.WARNING,
                    VerificationStatus.UNKNOWN,
                    (selected.metadata.source_id,),
                )
            )
        else:
            quantity = ceil_decimal(required / selected.maximum_dc_power_kwp)
    elif ranked:
        _, quantity, _, selected = min(ranked, key=lambda row: (row[0], row[1], row[2]))
    else:
        findings.append(
            Finding(
                "NO_ELIGIBLE_INVERTER",
                "No inverter with sourced DC capacity satisfies the mandatory filters.",
                FindingSeverity.BLOCKER,
                VerificationStatus.UNKNOWN,
            )
        )

    total_ac: Decimal | None = selected.ac_power_kw * quantity if selected else None
    total_dc = (
        selected.maximum_dc_power_kwp * quantity
        if selected and selected.maximum_dc_power_kwp is not None
        else None
    )
    ratio = required / total_ac if total_ac else None
    model_dc_ac_ratio = selected.dc_ac_ratio if selected else None
    source_ids = (selected.metadata.source_id,) if selected else ()
    if selected:
        findings.extend(
            rule_status_finding(
                "INV-DC-CAPACITY", selected.metadata.verification_status, source_ids
            )
        )
        if model_dc_ac_ratio is None:
            findings.append(
                Finding(
                    "INVERTER_DC_AC_RATIO_UNKNOWN",
                    "The selected model has no sourced DC/AC ratio; no global ratio was inferred.",
                    FindingSeverity.WARNING,
                    VerificationStatus.UNKNOWN,
                    source_ids,
                )
            )
        else:
            findings.append(
                Finding(
                    "INVERTER_DC_AC_RATIO_MODEL_SPECIFIC",
                    "The DC/AC ratio is an assumption scoped to this inverter model; "
                    "it is not applied as a global ratio.",
                    FindingSeverity.REVIEW,
                    VerificationStatus.ASSUMPTION,
                    source_ids,
                )
            )

    decision = DecisionRecord(
        decision_id=stable_decision_id(
            "INV-DC-CAPACITY", required, selected.record_id if selected else "NONE", quantity
        ),
        engine="inverter",
        rule_id="INV-DC-CAPACITY",
        rule_version="1.0",
        verification_status=selected_status,
        inputs=(
            TraceValue("required_dc_power", required, "kWp"),
            TraceValue("required_ac_voltage", voltage, "V"),
            TraceValue(
                "allowed_model_ids",
                "|".join(sorted(allowed_model_ids)) if allowed_model_ids is not None else None,
            ),
            TraceValue("override_model_id", override_model_id),
        ),
        calculated_values=(
            TraceValue("installed_ac_power", total_ac, "kW"),
            TraceValue("installed_dc_capacity", total_dc, "kWp"),
            TraceValue("requested_to_installed_ac_ratio", ratio, None),
            TraceValue("model_dc_ac_ratio", model_dc_ac_ratio, None),
        ),
        selected_values=(
            TraceValue("inverter_model_id", selected.record_id if selected else None),
            TraceValue("quantity", quantity),
            TraceValue("selected_model_dc_ac_ratio", model_dc_ac_ratio, None),
        ),
        candidates=tuple(candidate_records),
        source_ids=source_ids,
        findings=tuple(findings),
        override_reason=override_reason if override_model_id else None,
    )
    return InverterSelection(
        selected_model_id=selected.record_id if selected else None,
        quantity=quantity,
        required_dc_power_kwp=required,
        total_ac_power_kw=total_ac,
        total_dc_capacity_kwp=total_dc,
        dc_ac_ratio=ratio,
        findings=tuple(findings),
        decision=decision,
        selected_model_dc_ac_ratio=model_dc_ac_ratio,
    )


def calculate_ac_circuits(
    selection: InverterSelection,
    catalogue: Sequence[InverterSpec],
    *,
    power_factor: DecimalLike = Decimal("1"),
    efficiency: DecimalLike = Decimal("1"),
    circuit_prefix: str = "INV",
) -> tuple[CircuitRequirement, ...]:
    """Create one AC circuit requirement per selected inverter unit."""

    if selection.selected_model_id is None or selection.quantity == 0:
        return ()
    matches = [item for item in catalogue if item.record_id == selection.selected_model_id]
    if len(matches) != 1:
        raise EngineeringValidationError("catalogue", "must contain selected inverter exactly once")
    inverter = matches[0]
    pf = require_between_zero_and_one(power_factor, "power_factor")
    eta = require_between_zero_and_one(efficiency, "efficiency")
    circuits: list[CircuitRequirement] = []
    rule = RULES.get("AC-CURRENT")
    for index in range(1, selection.quantity + 1):
        findings = list(
            rule_status_finding(rule.rule_id, rule.verification_status, rule.source_ids)
        )
        if inverter.maximum_output_current_a is not None:
            current = inverter.maximum_output_current_a
            basis = "manufacturer_maximum_output_current"
            current_status = inverter.metadata.verification_status
        elif inverter.ac_voltage_v is None or inverter.phases is None:
            current = None
            basis = "not_assessed_missing_voltage_or_phase"
            current_status = VerificationStatus.UNKNOWN
            findings.append(
                Finding(
                    "INVERTER_CURRENT_NOT_ASSESSED",
                    "AC current is not assessed because sourced voltage or phase configuration "
                    "is missing; no value was inferred.",
                    FindingSeverity.WARNING,
                    current_status,
                    (inverter.metadata.source_id,),
                )
            )
        else:
            current = calculate_ac_current(
                inverter.ac_power_kw,
                inverter.ac_voltage_v,
                phases=inverter.phases,
                power_factor=pf,
                efficiency=eta,
            )
            basis = "calculated_fallback"
            current_status = VerificationStatus.ASSUMPTION
            findings.append(
                Finding(
                    "INVERTER_CURRENT_FALLBACK",
                    "Manufacturer maximum output current is missing; current was calculated "
                    "from power, voltage, PF and efficiency.",
                    FindingSeverity.WARNING,
                    current_status,
                    (inverter.metadata.source_id,),
                )
            )
        circuit_id = f"{circuit_prefix}-{index:03d}"
        decision = DecisionRecord(
            stable_decision_id("AC-CURRENT", circuit_id, current),
            "inverter",
            "AC-CURRENT",
            "1.0",
            current_status,
            (
                TraceValue("inverter_model_id", inverter.record_id),
                TraceValue("ac_power", inverter.ac_power_kw, "kW"),
                TraceValue("voltage", inverter.ac_voltage_v, "V"),
                TraceValue(
                    "manufacturer_maximum_output_current",
                    inverter.maximum_output_current_a,
                    "A",
                ),
                TraceValue("power_factor", pf),
                TraceValue("efficiency", eta),
                TraceValue("phases", inverter.phases.value if inverter.phases else None),
            ),
            calculated_values=(TraceValue("design_current", current, "A"),),
            selected_values=(TraceValue("current_basis", basis),),
            source_ids=(inverter.metadata.source_id,),
            findings=tuple(findings),
        )
        circuits.append(
            CircuitRequirement(
                circuit_id,
                inverter.record_id,
                1,
                inverter.phases,
                inverter.ac_voltage_v,
                inverter.ac_power_kw,
                current,
                basis,
                tuple(findings),
                decision,
            )
        )
    return tuple(circuits)
