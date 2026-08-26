"""Immutable records loaded by repository adapters into calculation engines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from solar_design.domain import (
    EngineeringValidationError,
    PhaseConfiguration,
    VerificationStatus,
)
from solar_design.validation.numeric import (
    require_between_zero_and_one,
    require_non_negative,
    require_positive,
)


@dataclass(frozen=True, slots=True)
class RecordMetadata:
    record_id: str
    revision: str
    verification_status: VerificationStatus
    source_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for name in ("record_id", "revision", "source_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.source_id.split("|") if part.strip())


@dataclass(frozen=True, slots=True)
class InverterSpec:
    metadata: RecordMetadata
    manufacturer: str
    model: str
    ac_power_kw: Decimal
    ac_voltage_v: Decimal | None
    phases: PhaseConfiguration | None = PhaseConfiguration.THREE_PHASE
    ac_apparent_power_kva: Decimal | None = None
    nominal_current_a: Decimal | None = None
    maximum_output_current_a: Decimal | None = None
    minimum_power_factor: Decimal | None = None
    maximum_dc_power_kwp: Decimal | None = None
    ambient_reference_c: Decimal | None = None
    mppt_count: int | None = None
    maximum_input_current_per_mppt_a: Decimal | None = None
    dc_ac_ratio: Decimal | None = None
    maximum_dc_input_current_a: Decimal | None = None

    def __post_init__(self) -> None:
        require_positive(self.ac_power_kw, "ac_power_kw")
        if self.ac_voltage_v is not None:
            require_positive(self.ac_voltage_v, "ac_voltage_v")
        if self.minimum_power_factor is not None:
            require_between_zero_and_one(self.minimum_power_factor, "minimum_power_factor")
        for name in (
            "ac_apparent_power_kva",
            "nominal_current_a",
            "maximum_output_current_a",
            "maximum_dc_power_kwp",
            "dc_ac_ratio",
            "maximum_dc_input_current_a",
            "maximum_input_current_per_mppt_a",
        ):
            value = getattr(self, name)
            if value is not None:
                require_positive(value, name)
        if self.mppt_count is not None and self.mppt_count <= 0:
            raise ValueError("mppt_count must be greater than zero")

    @property
    def record_id(self) -> str:
        return self.metadata.record_id


_MODEL_CSA_PATTERN = re.compile(
    r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:mm2|mm²|sq\.?\s*mm)\b",
    re.IGNORECASE,
)


def _model_csa_mm2(model: str) -> Decimal | None:
    """Extract an explicitly stated CSA from a cable model, if present."""

    matches = _MODEL_CSA_PATTERN.findall(model)
    if not matches:
        return None
    # A model must not contain conflicting explicit CSA labels.
    values = {Decimal(value) for value in matches}
    if len(values) != 1:
        raise EngineeringValidationError(
            "cable.model", "contains conflicting CSA labels", model
        )
    return values.pop()


@dataclass(frozen=True, slots=True)
class CableSpec:
    metadata: RecordMetadata
    manufacturer: str | None
    model: str
    family: str
    material: str | None
    insulation: str | None
    voltage_class_v: Decimal | None
    cores: int
    cross_section_mm2: Decimal
    outside_diameter_mm: Decimal | None
    temperature_rating_c: Decimal | None

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model must not be blank")
        if not self.family.strip():
            raise ValueError("family must not be blank")
        if self.voltage_class_v is not None:
            require_positive(self.voltage_class_v, "voltage_class_v")
        require_positive(self.cross_section_mm2, "cross_section_mm2")
        if self.temperature_rating_c is not None:
            require_positive(self.temperature_rating_c, "temperature_rating_c")
        if self.outside_diameter_mm is not None:
            require_positive(self.outside_diameter_mm, "outside_diameter_mm")
        if self.cores <= 0:
            raise ValueError("cores must be greater than zero")
        model_csa = _model_csa_mm2(self.model)
        if model_csa is not None and model_csa != self.cross_section_mm2:
            raise EngineeringValidationError(
                "cable.model",
                "model CSA does not match the structured cable CSA",
                {
                    "model": self.model,
                    "model_csa_mm2": model_csa,
                    "csa_mm2": self.cross_section_mm2,
                },
            )

    @property
    def record_id(self) -> str:
        return self.metadata.record_id


@dataclass(frozen=True, slots=True)
class AmpacityRecord:
    metadata: RecordMetadata
    cable_id: str
    installation_method: str
    current_carrying_conductors: int
    reference_ambient_c: Decimal
    ampacity_a: Decimal

    def __post_init__(self) -> None:
        if not self.cable_id.strip() or not self.installation_method.strip():
            raise ValueError("cable_id and installation_method must not be blank")
        if self.current_carrying_conductors <= 0:
            raise ValueError("current_carrying_conductors must be greater than zero")
        require_positive(self.ampacity_a, "ampacity_a")


@dataclass(frozen=True, slots=True)
class CorrectionFactor:
    """One explicitly sourced derating factor in an ampacity calculation chain."""

    metadata: RecordMetadata
    factor_type: str
    factor: Decimal
    label: str = ""
    conditions: str = ""

    def __post_init__(self) -> None:
        if not self.factor_type.strip():
            raise ValueError("factor_type must not be blank")
        require_between_zero_and_one(self.factor, "factor")

    @property
    def record_id(self) -> str:
        return self.metadata.record_id


@dataclass(frozen=True, slots=True)
class GroupingFactorSpec:
    """A grouping-factor table row retained as a selectable correction factor."""

    metadata: RecordMetadata
    installation_family: str
    min_groups: int
    max_groups: int
    factor: Decimal
    counting_basis: str
    conditions: str

    def __post_init__(self) -> None:
        if not self.installation_family.strip() or not self.counting_basis.strip():
            raise ValueError("installation_family and counting_basis must not be blank")
        if self.min_groups <= 0 or self.max_groups < self.min_groups:
            raise ValueError("group range is invalid")
        require_between_zero_and_one(self.factor, "factor")

    @property
    def record_id(self) -> str:
        return self.metadata.record_id

    def as_correction_factor(self) -> CorrectionFactor:
        return CorrectionFactor(
            metadata=self.metadata,
            factor_type="grouping",
            factor=self.factor,
            label=f"{self.installation_family}:{self.min_groups}-{self.max_groups}",
            conditions=self.conditions,
        )


@dataclass(frozen=True, slots=True)
class ProtectionCandidate:
    """Breaker candidate that can retain incomplete Draft catalogue data."""

    metadata: RecordMetadata
    role: str
    manufacturer: str | None = None
    model: str | None = None
    poles: int | None = None
    voltage_v: Decimal | None = None
    trip_setting_a: Decimal | None = None
    frame_rating_a: Decimal | None = None
    breaking_capacity_ka: Decimal | None = None
    terminal_temperature_c: Decimal | None = None
    adjustable_settings: str | None = None
    coordination_status: str = "NOT_ASSESSED"

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("role must not be blank")
        if self.poles is not None and self.poles <= 0:
            raise ValueError("poles must be greater than zero")
        for name in (
            "voltage_v",
            "trip_setting_a",
            "frame_rating_a",
            "breaking_capacity_ka",
            "terminal_temperature_c",
        ):
            value = getattr(self, name)
            if value is not None:
                require_positive(value, name)
        if self.trip_setting_a is not None and self.frame_rating_a is not None:
            if self.trip_setting_a > self.frame_rating_a:
                raise ValueError("trip_setting_a must not exceed frame_rating_a")

    @property
    def record_id(self) -> str:
        return self.metadata.record_id


@dataclass(frozen=True, slots=True)
class BreakerSpec:
    metadata: RecordMetadata
    manufacturer: str
    model: str
    poles: int
    voltage_v: Decimal
    frame_rating_a: Decimal
    trip_rating_a: Decimal
    breaking_capacity_ka: Decimal | None = None
    terminal_temperature_c: Decimal | None = None

    def __post_init__(self) -> None:
        if self.poles <= 0:
            raise ValueError("poles must be greater than zero")
        voltage = require_positive(self.voltage_v, "voltage_v")
        frame = require_positive(self.frame_rating_a, "frame_rating_a")
        trip = require_positive(self.trip_rating_a, "trip_rating_a")
        if trip > frame:
            raise ValueError("trip_rating_a must not exceed frame_rating_a")
        if voltage <= 0:  # pragma: no cover - kept explicit for domain readability
            raise ValueError("voltage_v must be positive")
        for name in ("breaking_capacity_ka", "terminal_temperature_c"):
            value = getattr(self, name)
            if value is not None:
                require_positive(value, name)

    @property
    def record_id(self) -> str:
        return self.metadata.record_id


@dataclass(frozen=True, slots=True)
class ConduitSpec:
    metadata: RecordMetadata
    conduit_type: str
    trade_size: str
    internal_diameter_mm: Decimal
    standard: str
    is_screening_dimension: bool = False

    def __post_init__(self) -> None:
        require_positive(self.internal_diameter_mm, "internal_diameter_mm")
        if not self.trade_size.strip():
            raise ValueError("trade_size must not be blank")

    @property
    def record_id(self) -> str:
        return self.metadata.record_id


@dataclass(frozen=True, slots=True)
class PESelectionRule:
    metadata: RecordMetadata
    phase_cross_section_mm2: Decimal
    pe_cross_section_mm2: Decimal | None
    phase_material: str = "CU"
    pe_material: str = "CU"

    def __post_init__(self) -> None:
        require_positive(self.phase_cross_section_mm2, "phase_cross_section_mm2")
        if self.pe_cross_section_mm2 is not None:
            require_positive(self.pe_cross_section_mm2, "pe_cross_section_mm2")


@dataclass(frozen=True, slots=True)
class TransformerSpec:
    metadata: RecordMetadata
    manufacturer: str | None
    model: str | None
    rating_kva: Decimal
    high_voltage_v: Decimal | None
    low_voltage_v: Decimal | None
    phases: PhaseConfiguration | None = PhaseConfiguration.THREE_PHASE
    vector_group: str | None = None
    impedance_percent: Decimal | None = None
    allowed_installation_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_positive(self.rating_kva, "rating_kva")
        if self.high_voltage_v is not None:
            require_positive(self.high_voltage_v, "high_voltage_v")
        if self.low_voltage_v is not None:
            require_positive(self.low_voltage_v, "low_voltage_v")
        if self.impedance_percent is not None:
            require_non_negative(self.impedance_percent, "impedance_percent")

    @property
    def record_id(self) -> str:
        return self.metadata.record_id
