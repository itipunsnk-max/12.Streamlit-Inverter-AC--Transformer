"""Application-layer workflow orchestration for the Streamlit coordinator.

This module is the boundary between presentation state and pure engineering
engines. Page modules never perform catalogue adaptation or costing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from solar_design.boq import BOQRevision, boq_template_from_snapshot, generate_boq
from solar_design.boq.models import LinePrice, PricingMode
from solar_design.calculations.ampacity import check_70c_ampacity, strict_70c_required_ampacity
from solar_design.calculations.inverter import (
    calculate_ac_circuits,
    inverter_specs_from_snapshot,
    select_inverters,
)
from solar_design.calculations.protection import select_protection
from solar_design.calculations.transformer import (
    required_transformer_kva_from_load,
    size_transformer,
    standard_transformer_ratings_from_snapshot,
)
from solar_design.calculations.wiring import (
    allocate_parallel_circuit_conduits,
    ampacity_records_from_snapshot,
    cable_specs_from_snapshot,
    conduit_specs_from_snapshot,
    pe_selection_rules_from_snapshot,
    select_cables_and_pe,
)
from solar_design.costing import CostRevision, RateRecord, RateSnapshot, calculate_cost
from solar_design.domain import (
    EngineeringValidationError,
    PhaseConfiguration,
    TransformerDuty,
)
from solar_design.models import (
    AmpacityAssessment,
    CircuitRequirement,
    ConduitAllocation,
    InverterSelection,
    InverterSpec,
    ProtectionSelection,
    ReferenceSnapshot,
    TransformerSelection,
    WiringSelection,
)
from solar_design.repositories import ReleaseRepository


@dataclass(frozen=True, slots=True)
class ProjectInputs:
    """User-owned project basis; no calculated engineering values are stored here."""

    project_name: str = "Solar AC design"
    required_dc_power_kwp: Decimal = Decimal("100")
    required_ac_voltage_v: Decimal | None = None
    load_kw: Decimal = Decimal("100")
    power_factor: Decimal = Decimal("0.95")
    demand_factor: Decimal = Decimal("0.80")
    spare_percent: Decimal = Decimal("10")
    derating_factor: Decimal = Decimal("0.95")
    installation_type: str = "YARD"
    transformer_count: int = 1
    duty: TransformerDuty = TransformerDuty.EQUAL_SHARING
    high_voltage_v: Decimal = Decimal("22000")
    low_voltage_v: Decimal = Decimal("400")
    override_inverter_model_id: str | None = None
    override_transformer_rating_kva: Decimal | None = None
    override_reason: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowResults:
    inverter: InverterSelection | None = None
    circuits: tuple[CircuitRequirement, ...] = ()
    protection: ProtectionSelection | None = None
    ampacity: AmpacityAssessment | None = None
    wiring: WiringSelection | None = None
    conduit: ConduitAllocation | None = None
    transformer: TransformerSelection | None = None
    boq: BOQRevision | None = None
    cost: CostRevision | None = None


@dataclass(frozen=True, slots=True)
class CircuitWiringResults:
    """Engineering results for one selected inverter AC circuit."""

    protection: ProtectionSelection
    ampacity: AmpacityAssessment
    wiring: WiringSelection
    conduit: ConduitAllocation


def assess_inverter_ac_circuit(
    design_current_a: Decimal,
    inverter: InverterSpec,
    snapshot: ReferenceSnapshot,
) -> CircuitWiringResults:
    """Assess a 70 C AC feeder, exact PE, and one complete set per conduit.

    This application service is shared by the full workflow and the external
    inverter-reference view.  Presentation modules receive results only; they
    do not reproduce engineering rules or catalogue lookups.
    """

    protection = select_protection(design_current_a)
    required_ampacity = strict_70c_required_ampacity(design_current_a)
    all_cables = cable_specs_from_snapshot(snapshot)
    phase_cables = tuple(item for item in all_cables if item.system == "AC")
    linked_ampacity = ampacity_records_from_snapshot(snapshot, phase_cables)
    wiring = select_cables_and_pe(
        required_ampacity,
        phase_cables,
        linked_ampacity,
        pe_selection_rules_from_snapshot(snapshot),
        installation_method="UNSPECIFIED",
        current_carrying_conductors=3,
        max_parallel_runs=3,
    )
    if wiring.cable.cable_id is None or wiring.cable.ampacity_per_run_a is None:
        raise EngineeringValidationError(
            "cable_selection",
            "No eligible 70 C phase-cable selection is available for this inverter",
        )

    selected_cable = next(
        item for item in phase_cables if item.record_id == wiring.cable.cable_id
    )
    ampacity = check_70c_ampacity(
        design_current_a,
        wiring.cable.ampacity_per_run_a,
        cable_cross_section_mm2=selected_cable.cross_section_mm2,
    )

    pe_cable = None
    if wiring.protective_earth.pe_cross_section_mm2 is not None:
        pe_matches = tuple(
            item
            for item in all_cables
            if item.system == "GROUND"
            and item.cross_section_mm2
            == wiring.protective_earth.pe_cross_section_mm2
        )
        if len(pe_matches) > 1:
            raise EngineeringValidationError(
                "pe_cable_selection",
                "Multiple PE cable records match the exact selected CSA",
            )
        pe_cable = pe_matches[0] if pe_matches else None

    if inverter.phases is None:
        raise EngineeringValidationError(
            "inverter.phases",
            "Inverter phase configuration is required for conduit allocation",
        )
    if inverter.ac_connection not in {"3-N-PE", "3-PE"}:
        raise EngineeringValidationError(
            "inverter.ac_connection",
            "Supported AC connection must be exactly 3-N-PE or 3-PE",
        )
    phase_conductors = 3 if inverter.phases is PhaseConfiguration.THREE_PHASE else 1
    neutral_conductors = 1 if inverter.ac_connection == "3-N-PE" else 0
    conduit = allocate_parallel_circuit_conduits(
        selected_cable,
        pe_cable,
        conduit_specs_from_snapshot(snapshot),
        phase_conductors_per_run=phase_conductors,
        neutral_conductors_per_run=neutral_conductors,
        parallel_runs=wiring.cable.parallel_runs,
    )
    return CircuitWiringResults(
        protection=protection,
        ampacity=ampacity,
        wiring=wiring,
        conduit=conduit,
    )


def load_reference_snapshot(
    release_dir: str | Path,
) -> tuple[ReferenceSnapshot, tuple[tuple[str, str], ...]]:
    """Load the pinned release and expose display options without page lookups."""

    snapshot = ReleaseRepository(release_dir).load_snapshot()
    inverter_options = tuple(
        (
            record.record_id,
            f"{record.manufacturer} {record.model} ({record.ac_power_kw} kW)",
        )
        for record in snapshot.inverters
    )
    return snapshot, inverter_options


def run_design_workflow(
    inputs: ProjectInputs,
    snapshot: ReferenceSnapshot,
    revision: int,
) -> WorkflowResults:
    """Run the dependency graph without importing Streamlit or session state."""

    inverter_catalogue = inverter_specs_from_snapshot(snapshot)
    inverter = select_inverters(
        inputs.required_dc_power_kwp,
        inverter_catalogue,
        required_ac_voltage_v=inputs.required_ac_voltage_v,
        override_model_id=inputs.override_inverter_model_id,
        override_reason=inputs.override_reason,
    )
    circuits = calculate_ac_circuits(inverter, inverter_catalogue)
    current = next(
        (item.design_current_a for item in circuits if item.design_current_a is not None),
        None,
    )

    protection = None
    ampacity = None
    wiring = None
    conduit = None
    if current is not None:
        selected_inverter = next(
            item for item in inverter_catalogue if item.record_id == inverter.selected_model_id
        )
        circuit_results = assess_inverter_ac_circuit(
            current,
            selected_inverter,
            snapshot,
        )
        protection = circuit_results.protection
        ampacity = circuit_results.ampacity
        wiring = circuit_results.wiring
        conduit = circuit_results.conduit

    required_transformer = required_transformer_kva_from_load(
        inputs.load_kw,
        demand_factor=inputs.demand_factor,
        power_factor=inputs.power_factor,
        spare_percent=inputs.spare_percent,
        derating_factor=inputs.derating_factor,
    )
    transformer = size_transformer(
        required_transformer,
        standard_ratings_kva=standard_transformer_ratings_from_snapshot(snapshot),
        transformer_count=inputs.transformer_count,
        duty=inputs.duty,
        high_voltage_v=inputs.high_voltage_v,
        low_voltage_v=inputs.low_voltage_v,
        phases=next(
            (item.phases for item in inverter_catalogue if item.phases is not None),
            None,
        )
        or PhaseConfiguration.THREE_PHASE,
        installation_type=inputs.installation_type,
        override_rating_per_unit_kva=inputs.override_transformer_rating_kva,
        override_reason=inputs.override_reason,
    )

    boq = None
    cost = None
    if inputs.installation_type == "YARD":
        template = boq_template_from_snapshot(snapshot, installation_type=inputs.installation_type)
        design_run = {
            "design_run_id": f"ui-run-{revision}",
            "installation_type": inputs.installation_type,
            "transformer": {"count": inputs.transformer_count},
            "transformer_selection": transformer.selected_rating_per_unit_kva,
        }
        boq = generate_boq(design_run, template)
        cost = calculate_cost(boq, _rate_snapshot(snapshot))

    return WorkflowResults(
        inverter=inverter,
        circuits=circuits,
        protection=protection,
        ampacity=ampacity,
        wiring=wiring,
        conduit=conduit,
        transformer=transformer,
        boq=boq,
        cost=cost,
    )


def _line_price(value: Decimal | None) -> LinePrice | None:
    if value is None:
        return None
    return LinePrice(PricingMode.COMPOSITE, composite=value)


def _rate_snapshot(snapshot: ReferenceSnapshot) -> RateSnapshot:
    rates: list[RateRecord] = []
    seen_ids: set[str] = set()
    for record in snapshot.unit_rates:
        # Release BOQ rows may link a unit rate by either its stable record_id
        # (for example RATE-LA-24KV-5KA-3P) or its commercial item_code (for
        # example LA-24KV-5KA-3P).  Preserve both explicit identifiers as
        # aliases so a valid release link cannot silently become MISSING_RATE.
        aliases = tuple(dict.fromkeys((record.record_id, record.item_code)))
        for rate_id in aliases:
            if rate_id in seen_ids:
                raise ValueError(f"duplicate unit-rate identifier in release: {rate_id}")
            seen_ids.add(rate_id)
            rates.append(
                RateRecord(
                    rate_id=rate_id,
                    base=_line_price(record.base_price_thb),
                    low=_line_price(record.low_price_thb),
                    high=_line_price(record.high_price_thb),
                    currency=record.currency,
                    valid_from=record.source_date.isoformat() if record.source_date else None,
                    source_ids=record.source_ids,
                    verification_status=record.verification_status,
                    notes=(record.notes,) if record.notes else (),
                )
            )
    return RateSnapshot(
        snapshot_id=f"rates-{snapshot.data_version}",
        data_version=snapshot.data_version,
        rates=tuple(rates),
    )
