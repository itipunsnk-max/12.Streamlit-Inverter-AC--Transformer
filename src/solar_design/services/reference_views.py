"""Read-only reference views composed from validated engineering services."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from solar_design.calculations.inverter import inverter_specs_from_snapshot
from solar_design.calculations.wiring import (
    cable_specs_from_snapshot,
    conduit_specs_from_snapshot,
)
from solar_design.domain import AssessmentStatus, EngineeringValidationError
from solar_design.models import ReferenceSnapshot

from .workflow import assess_inverter_ac_circuit


@dataclass(frozen=True, slots=True)
class InverterWiringReference:
    """One manufacturer inverter and its independent AC feeder assessment."""

    inverter_id: str
    manufacturer: str
    model: str
    rated_ac_kw: Decimal
    ac_voltage_v: Decimal | None
    ac_connection: str | None
    maximum_ac_current_a: Decimal | None
    dc_max_voltage_v: Decimal | None
    startup_voltage_v: Decimal | None
    mppt_range_v: str
    mppt_count: int | None
    inputs_per_mppt: int | None
    maximum_input_current_per_mppt_a: Decimal | None
    maximum_short_circuit_current_per_mppt_a: Decimal | None
    required_70c_ampacity_a: Decimal | None
    main_cable_id: str | None
    main_cable_csa_mm2: Decimal | None
    main_cable_od_mm: Decimal | None
    parallel_runs: int | None
    conductors_per_conduit: int | None
    pe_cable_id: str | None
    pe_cable_csa_mm2: Decimal | None
    conduit_id: str | None
    conduit_trade_size: str | None
    conduit_count: int
    permitted_fill_percent: Decimal | None
    maximum_actual_fill_percent: Decimal | None
    status: AssessmentStatus
    review_items: tuple[str, ...]


class _InverterReferenceBase(TypedDict):
    inverter_id: str
    manufacturer: str
    model: str
    rated_ac_kw: Decimal
    ac_voltage_v: Decimal | None
    ac_connection: str | None
    maximum_ac_current_a: Decimal | None
    dc_max_voltage_v: Decimal | None
    startup_voltage_v: Decimal | None
    mppt_range_v: str
    mppt_count: int | None
    inputs_per_mppt: int | None
    maximum_input_current_per_mppt_a: Decimal | None
    maximum_short_circuit_current_per_mppt_a: Decimal | None


def _aggregate_status(*statuses: AssessmentStatus) -> AssessmentStatus:
    if AssessmentStatus.FAIL in statuses:
        return AssessmentStatus.FAIL
    if AssessmentStatus.MISSING in statuses:
        return AssessmentStatus.MISSING
    if statuses and all(item is AssessmentStatus.PASS for item in statuses):
        return AssessmentStatus.PASS
    return AssessmentStatus.NOT_ASSESSED


def inverter_wiring_references(
    snapshot: ReferenceSnapshot,
) -> tuple[InverterWiringReference, ...]:
    """Build one-inverter-per-feeder reference rows without running a project."""

    inverters = inverter_specs_from_snapshot(snapshot)
    cables = cable_specs_from_snapshot(snapshot)
    cable_by_id = {item.record_id: item for item in cables}
    conduits = conduit_specs_from_snapshot(snapshot)
    conduit_by_id = {item.record_id: item for item in conduits}
    rows: list[InverterWiringReference] = []

    for inverter in inverters:
        current = inverter.maximum_output_current_a
        base: _InverterReferenceBase = dict(
            inverter_id=inverter.record_id,
            manufacturer=inverter.manufacturer,
            model=inverter.model,
            rated_ac_kw=inverter.ac_power_kw,
            ac_voltage_v=inverter.ac_voltage_v,
            ac_connection=inverter.ac_connection,
            maximum_ac_current_a=current,
            dc_max_voltage_v=inverter.dc_max_voltage_v,
            startup_voltage_v=inverter.startup_voltage_v,
            mppt_range_v=(
                f"{inverter.mppt_min_voltage_v}-{inverter.mppt_max_voltage_v}"
                if inverter.mppt_min_voltage_v is not None
                and inverter.mppt_max_voltage_v is not None
                else "MISSING"
            ),
            mppt_count=inverter.mppt_count,
            inputs_per_mppt=inverter.inputs_per_mppt,
            maximum_input_current_per_mppt_a=(
                inverter.maximum_input_current_per_mppt_a
            ),
            maximum_short_circuit_current_per_mppt_a=(
                inverter.max_short_circuit_current_per_mppt_a
            ),
        )
        if current is None:
            rows.append(
                InverterWiringReference(
                    **base,
                    required_70c_ampacity_a=None,
                    main_cable_id=None,
                    main_cable_csa_mm2=None,
                    main_cable_od_mm=None,
                    parallel_runs=None,
                    conductors_per_conduit=None,
                    pe_cable_id=None,
                    pe_cable_csa_mm2=None,
                    conduit_id=None,
                    conduit_trade_size=None,
                    conduit_count=0,
                    permitted_fill_percent=None,
                    maximum_actual_fill_percent=None,
                    status=AssessmentStatus.MISSING,
                    review_items=("Manufacturer maximum AC current is missing",),
                )
            )
            continue

        try:
            result = assess_inverter_ac_circuit(current, inverter, snapshot)
        except EngineeringValidationError as exc:
            rows.append(
                InverterWiringReference(
                    **base,
                    required_70c_ampacity_a=None,
                    main_cable_id=None,
                    main_cable_csa_mm2=None,
                    main_cable_od_mm=None,
                    parallel_runs=None,
                    conductors_per_conduit=None,
                    pe_cable_id=None,
                    pe_cable_csa_mm2=None,
                    conduit_id=None,
                    conduit_trade_size=None,
                    conduit_count=0,
                    permitted_fill_percent=None,
                    maximum_actual_fill_percent=None,
                    status=AssessmentStatus.MISSING,
                    review_items=(str(exc),),
                )
            )
            continue

        phase_cable = (
            cable_by_id.get(result.wiring.cable.cable_id)
            if result.wiring.cable.cable_id
            else None
        )
        pe_cable = next(
            (
                item
                for item in cables
                if item.system == "GROUND"
                and item.cross_section_mm2
                == result.wiring.protective_earth.pe_cross_section_mm2
            ),
            None,
        )
        conduit = (
            conduit_by_id.get(result.conduit.conduit_id)
            if result.conduit.conduit_id
            else None
        )
        findings = (
            result.wiring.cable.findings
            + result.wiring.protective_earth.findings
            + result.wiring.findings
            + result.conduit.findings
        )
        review_items = tuple(dict.fromkeys(item.message for item in findings))
        runs = result.conduit.runs
        rows.append(
            InverterWiringReference(
                **base,
                required_70c_ampacity_a=result.ampacity.strict_70c_required_ampacity_a,
                main_cable_id=result.wiring.cable.cable_id,
                main_cable_csa_mm2=(
                    phase_cable.cross_section_mm2 if phase_cable else None
                ),
                main_cable_od_mm=(phase_cable.outside_diameter_mm if phase_cable else None),
                parallel_runs=result.wiring.cable.parallel_runs,
                conductors_per_conduit=(runs[0].cable_count if runs else None),
                pe_cable_id=(pe_cable.record_id if pe_cable else None),
                pe_cable_csa_mm2=result.wiring.protective_earth.pe_cross_section_mm2,
                conduit_id=result.conduit.conduit_id,
                conduit_trade_size=(conduit.trade_size if conduit else None),
                conduit_count=len(runs),
                permitted_fill_percent=(runs[0].permitted_fill_percent if runs else None),
                maximum_actual_fill_percent=(
                    max(item.actual_fill_percent for item in runs) if runs else None
                ),
                status=_aggregate_status(
                    result.wiring.cable.status,
                    result.wiring.protective_earth.status,
                    result.conduit.status,
                ),
                review_items=review_items,
            )
        )

    return tuple(rows)
