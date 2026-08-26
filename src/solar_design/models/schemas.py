"""Pydantic contracts for the versioned reference-data release.

CSV is an interchange format only.  The repository loader normalizes empty
cells to ``None`` and validates each row with these frozen models before any
calculation engine can receive it.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

from solar_design.domain import FindingSeverity, PhaseConfiguration, VerificationStatus

CURRENT_SCHEMA_VERSION = "1.0.0"
KNOWN_EXPRESSION_KEYS = frozenset(
    {
        "catalogue_maximum_dc_power",
        "ac_current_by_phase",
        "strict_terminal_temperature_conversion",
        "physical_cable_area_fill",
        "exact_phase_to_pe_lookup",
        "load_demand_pf_spare_derating",
        "pv_pf_margin_derating",
        "not_assessed",
    }
)


class ReferenceRecord(BaseModel):
    """Fields shared by all data rows other than the source registry."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    record_id: str = Field(min_length=1)
    schema_version: str = CURRENT_SCHEMA_VERSION
    data_version: str = Field(min_length=1)
    revision: PositiveInt
    verification_status: VerificationStatus
    source_id: str = Field(min_length=1)
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str = ""

    @field_validator("source_id")
    @classmethod
    def validate_source_ids(cls, value: str) -> str:
        source_ids = tuple(part.strip() for part in value.split("|") if part.strip())
        if not source_ids:
            raise ValueError("source_id must contain at least one source ID")
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_id must not repeat a source ID")
        return "|".join(source_ids)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("schema_version must not be blank")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> ReferenceRecord:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(part for part in self.source_id.split("|") if part)


class SourceRecord(BaseModel):
    """Source registry row; ``source_id`` is its primary key."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    source_id: str = Field(min_length=1)
    schema_version: str = CURRENT_SCHEMA_VERSION
    data_version: str = Field(min_length=1)
    revision: PositiveInt
    title: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    edition_or_date: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    byte_size: NonNegativeInt
    authority: str = Field(min_length=1)
    licensing_status: str = Field(min_length=1)
    verification_status: VerificationStatus
    reviewer: str | None = None
    review_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str = ""

    @model_validator(mode="after")
    def validate_dates(self) -> SourceRecord:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class InverterRecord(ReferenceRecord):
    manufacturer: str = Field(min_length=1)
    model: str = Field(min_length=1)
    dc_max_voltage_v: Decimal | None = Field(default=None, gt=0)
    startup_voltage_v: Decimal | None = Field(default=None, gt=0)
    mppt_min_voltage_v: Decimal | None = Field(default=None, gt=0)
    mppt_max_voltage_v: Decimal | None = Field(default=None, gt=0)
    max_input_current_per_mppt_a: Decimal | None = Field(default=None, gt=0)
    max_short_circuit_current_per_mppt_a: Decimal | None = Field(default=None, gt=0)
    inputs_per_mppt: PositiveInt | None = None
    ac_power_kw: Decimal = Field(gt=0)
    ac_apparent_power_kva: Decimal | None = Field(default=None, gt=0)
    nominal_voltage_v: Decimal | None = Field(default=None, gt=0)
    phases: PhaseConfiguration | None = None
    pf_min: Decimal | None = Field(default=None, gt=0, le=1)
    pf_max: Decimal | None = Field(default=None, gt=0, le=1)
    nominal_ac_current_a: Decimal | None = Field(default=None, gt=0)
    max_ac_current_a: Decimal | None = Field(default=None, gt=0)
    recommended_max_dc_kwp: Decimal | None = Field(default=None, gt=0)
    dc_ac_ratio: Decimal | None = Field(default=None, gt=0)
    mppt_count: PositiveInt | None = None
    max_dc_input_current_a: Decimal | None = Field(default=None, gt=0)
    ac_connection: str | None = None
    input_current_basis: str | None = None
    ambient_reference_c: Decimal | None = None
    derating_profile: str | None = None

    @model_validator(mode="after")
    def validate_power_factor_range(self) -> InverterRecord:
        if self.pf_min and self.pf_max and self.pf_min > self.pf_max:
            raise ValueError("pf_min must not exceed pf_max")
        return self


class CableRecord(ReferenceRecord):
    system: str = Field(min_length=1)
    manufacturer: str | None = None
    family: str = Field(min_length=1)
    model: str = Field(min_length=1)
    conductor_material: str | None = None
    insulation: str | None = None
    voltage_class_v: Decimal | None = Field(default=None, gt=0)
    cores: PositiveInt
    csa_mm2: Decimal = Field(gt=0)
    outside_diameter_mm: Decimal | None = Field(default=None, gt=0)
    od_basis: str = Field(min_length=1)
    conductor_temp_c: Decimal | None = Field(default=None, gt=0)
    intended_use: str = Field(min_length=1)


class AmpacityRecord(ReferenceRecord):
    table_id: str = Field(min_length=1)
    cable_family: str = Field(min_length=1)
    conductor_material: str = Field(min_length=1)
    insulation: str = Field(min_length=1)
    conductor_temp_c: Decimal = Field(gt=0)
    installation_group: str = Field(min_length=1)
    installation_method: str = Field(min_length=1)
    cores: PositiveInt
    current_carrying_conductors: PositiveInt
    csa_mm2: Decimal = Field(gt=0)
    ampacity_a: Decimal = Field(gt=0)
    reference_ambient_c: Decimal = Field(gt=0)
    applicability: str = Field(min_length=1)


class GroupingFactorRecord(ReferenceRecord):
    installation_family: str = Field(min_length=1)
    min_groups: PositiveInt
    max_groups: PositiveInt
    factor: Decimal = Field(gt=0, le=1)
    counting_basis: str = Field(min_length=1)
    conditions: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_group_range(self) -> GroupingFactorRecord:
        if self.max_groups < self.min_groups:
            raise ValueError("max_groups must be on or after min_groups")
        return self


class BreakerRecord(ReferenceRecord):
    manufacturer: str | None = None
    model: str | None = None
    role: str = Field(min_length=1)
    poles: PositiveInt | None = None
    voltage_v: Decimal | None = Field(default=None, gt=0)
    trip_setting_a: Decimal | None = Field(default=None, gt=0)
    frame_rating_a: Decimal | None = Field(default=None, gt=0)
    breaking_capacity_ka: Decimal | None = Field(default=None, gt=0)
    terminal_temp_c: Decimal | None = Field(default=None, gt=0)
    adjustable_settings: str | None = None
    coordination_status: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_breaker_ratings(self) -> BreakerRecord:
        if (
            self.trip_setting_a is not None
            and self.frame_rating_a is not None
            and self.trip_setting_a > self.frame_rating_a
        ):
            raise ValueError("trip_setting_a must not exceed frame_rating_a")
        return self


class ConduitRecord(ReferenceRecord):
    manufacturer: str = Field(min_length=1)
    series: str = Field(min_length=1)
    item_number: str = Field(min_length=1)
    trade_size_in: str = Field(min_length=1)
    outside_diameter_mm: Decimal = Field(gt=0)
    minimum_wall_mm: Decimal = Field(gt=0)
    length_mm: Decimal = Field(gt=0)
    nominal_weight_kg: Decimal = Field(gt=0)
    primary_bundle_qty: PositiveInt | None = None
    master_bundle_qty: PositiveInt | None = None
    screening_internal_diameter_mm: Decimal = Field(gt=0)
    screening_internal_area_mm2: Decimal = Field(gt=0)
    certified_internal_diameter_mm: Decimal | None = Field(default=None, gt=0)
    standard_listing: str = Field(min_length=1)
    id_basis: str = Field(min_length=1)


class PEMappingRecord(ReferenceRecord):
    phase_material: str = Field(min_length=1)
    pe_material: str = Field(min_length=1)
    phase_csa_mm2: Decimal = Field(gt=0)
    pe_csa_mm2: Decimal = Field(gt=0)
    rule_family: str = Field(min_length=1)
    applicability: str = Field(min_length=1)


class TransformerRecord(ReferenceRecord):
    manufacturer: str | None = None
    model: str | None = None
    transformer_type: str = Field(min_length=1)
    rating_kva: Decimal = Field(gt=0)
    hv_voltage_v: Decimal | None = Field(default=None, gt=0)
    lv_voltage_v: Decimal | None = Field(default=None, gt=0)
    phases: PhaseConfiguration | None = None
    vector_group: str | None = None
    impedance_pct: Decimal | None = Field(default=None, ge=0)
    loss_class: str | None = None
    installation_eligibility: str = Field(min_length=1)
    availability_status: str = Field(min_length=1)


class TransformerPriceRecord(ReferenceRecord):
    manufacturer: str = Field(min_length=1)
    quotation_number: str | None = None
    quotation_date: date = Field()
    rating_kva: Decimal = Field(gt=0)
    hv_voltage_v: Decimal = Field(gt=0)
    lv_voltage_v: str = Field(min_length=1)
    unit_price_thb: Decimal = Field(gt=0)
    vat_included: str = Field(min_length=1)
    delivery_included: str | None = None
    crane_included: str | None = None
    installation_included: str | None = None
    testing_included: str | None = None
    utility_inspection_included: str | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def validate_price_dates(self) -> TransformerPriceRecord:
        if self.valid_until and self.valid_until < self.quotation_date:
            raise ValueError("valid_until must be on or after quotation_date")
        return self


class UnitRateRecord(ReferenceRecord):
    item_code: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description_th: str = Field(min_length=1)
    description_en: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    low_price_thb: Decimal | None = Field(default=None, ge=0)
    base_price_thb: Decimal | None = Field(default=None, ge=0)
    high_price_thb: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(min_length=1)
    source_date: date | None = None
    included_scope: str | None = None
    excluded_scope: str | None = None
    duplicate_scope_group: str | None = None


class DesignRuleRecord(ReferenceRecord):
    domain: str = Field(min_length=1)
    rule_type: str = Field(min_length=1)
    utility_profile: str = Field(min_length=1)
    applicability: str = Field(min_length=1)
    expression_key: str = Field(min_length=1)
    parameters_json: str = Field(min_length=2)
    outcome: str = Field(min_length=1)
    severity: FindingSeverity
    override_policy: str = Field(min_length=1)

    _known_expression_keys: ClassVar[frozenset[str]] = KNOWN_EXPRESSION_KEYS

    @field_validator("expression_key")
    @classmethod
    def validate_expression_key(cls, value: str) -> str:
        if value not in cls._known_expression_keys:
            raise ValueError(f"unknown expression_key: {value}")
        return value

    @field_validator("parameters_json")
    @classmethod
    def validate_parameters_json(cls, value: str) -> str:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("parameters_json must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("parameters_json must encode a JSON object")
        return value


class BOQTemplateRecord(ReferenceRecord):
    installation_type: str = Field(min_length=1)
    condition_key: str = Field(min_length=1)
    item_code: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description_th: str = Field(min_length=1)
    description_en: str = Field(min_length=1)
    quantity_rule_key: str = Field(min_length=1)
    default_quantity: Decimal | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1)
    rate_id: str | None = None
    pricing_mode: str = Field(min_length=1)
    cost_status: str = Field(min_length=1)
    duplicate_scope_group: str | None = None
    editable: bool
    display_order: NonNegativeInt


DATASET_MODELS: dict[str, type[ReferenceRecord] | type[SourceRecord]] = {
    "inverters.csv": InverterRecord,
    "cables.csv": CableRecord,
    "ampacity.csv": AmpacityRecord,
    "grouping_factors.csv": GroupingFactorRecord,
    "breakers.csv": BreakerRecord,
    "conduits.csv": ConduitRecord,
    "pe_mapping.csv": PEMappingRecord,
    "transformers.csv": TransformerRecord,
    "transformer_prices.csv": TransformerPriceRecord,
    "unit_rates.csv": UnitRateRecord,
    "design_rules.csv": DesignRuleRecord,
    "boq_templates.csv": BOQTemplateRecord,
    "sources.csv": SourceRecord,
}
