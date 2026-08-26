"""Immutable outputs returned by pure calculation functions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from solar_design.domain import (
    AssessmentStatus,
    DecisionRecord,
    Finding,
    PhaseConfiguration,
    TransformerDuty,
)


@dataclass(frozen=True, slots=True)
class InverterSelection:
    selected_model_id: str | None
    quantity: int
    required_dc_power_kwp: Decimal
    total_ac_power_kw: Decimal | None
    total_dc_capacity_kwp: Decimal | None
    dc_ac_ratio: Decimal | None
    findings: tuple[Finding, ...]
    decision: DecisionRecord
    selected_model_dc_ac_ratio: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CircuitRequirement:
    circuit_id: str
    equipment_id: str
    quantity: int
    phases: PhaseConfiguration | None
    voltage_v: Decimal | None
    ac_power_kw: Decimal
    design_current_a: Decimal | None
    current_basis: str
    findings: tuple[Finding, ...]
    decision: DecisionRecord


@dataclass(frozen=True, slots=True)
class ProtectionSelection:
    status: AssessmentStatus
    load_current_a: Decimal
    selected_breaker_id: str | None
    findings: tuple[Finding, ...]
    decision: DecisionRecord


@dataclass(frozen=True, slots=True)
class AmpacityAssessment:
    status: AssessmentStatus
    load_current_a: Decimal
    strict_70c_required_ampacity_a: Decimal
    corrected_required_table_ampacity_a: Decimal
    available_corrected_ampacity_a: Decimal
    correction_factor_product: Decimal
    estimated_conductor_temperature_c: Decimal | None
    findings: tuple[Finding, ...]
    decision: DecisionRecord


@dataclass(frozen=True, slots=True)
class CableSelection:
    status: AssessmentStatus
    cable_id: str | None
    parallel_runs: int
    ampacity_per_run_a: Decimal | None
    total_ampacity_a: Decimal | None
    findings: tuple[Finding, ...]
    decision: DecisionRecord


@dataclass(frozen=True, slots=True)
class PESelection:
    status: AssessmentStatus
    phase_cross_section_mm2: Decimal
    pe_cross_section_mm2: Decimal | None
    findings: tuple[Finding, ...]
    decision: DecisionRecord


@dataclass(frozen=True, slots=True)
class WiringSelection:
    cable: CableSelection
    protective_earth: PESelection
    voltage_drop_status: AssessmentStatus = AssessmentStatus.NOT_ASSESSED
    short_circuit_status: AssessmentStatus = AssessmentStatus.NOT_ASSESSED
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class ConduitRun:
    conduit_id: str
    cable_indices: tuple[int, ...]
    cable_count: int
    occupied_area_mm2: Decimal
    internal_area_mm2: Decimal
    permitted_fill_percent: Decimal
    actual_fill_percent: Decimal


@dataclass(frozen=True, slots=True)
class ConduitAllocation:
    status: AssessmentStatus
    conduit_id: str | None
    runs: tuple[ConduitRun, ...]
    findings: tuple[Finding, ...]
    decision: DecisionRecord


@dataclass(frozen=True, slots=True)
class TransformerSelection:
    status: AssessmentStatus
    duty: TransformerDuty
    transformer_count: int
    required_bank_kva: Decimal
    required_per_unit_kva: Decimal
    selected_rating_per_unit_kva: Decimal | None
    installed_bank_kva: Decimal | None
    normal_utilization_percent: Decimal | None
    contingency_utilization_percent: Decimal | None
    high_voltage_current_per_unit_a: Decimal | None
    low_voltage_current_per_unit_a: Decimal | None
    installation_status: AssessmentStatus
    findings: tuple[Finding, ...]
    decision: DecisionRecord
