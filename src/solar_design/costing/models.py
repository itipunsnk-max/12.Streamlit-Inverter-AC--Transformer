"""Cost catalogue and result models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from solar_design.boq import CostStatus, LinePrice
from solar_design.domain import Finding, VerificationStatus
from solar_design.validation.numeric import as_decimal, require_non_negative


class CostScenario(StrEnum):
    LOW = "LOW"
    BASE = "BASE"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class RateRecord:
    rate_id: str
    base: LinePrice | None = None
    low: LinePrice | None = None
    high: LinePrice | None = None
    currency: str = "THB"
    valid_from: str | None = None
    valid_until: str | None = None
    source_ids: tuple[str, ...] = ()
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rate_id.strip():
            raise ValueError("rate_id must not be blank")
        if self.currency != "THB":
            raise ValueError("v1 costing supports THB only")
        modes = {
            candidate.mode
            for candidate in (self.low, self.base, self.high)
            if candidate is not None
        }
        if len(modes) > 1:
            raise ValueError("all scenarios in one rate record must use the same pricing mode")

    def price_for(self, scenario: CostScenario) -> tuple[LinePrice | None, bool]:
        if scenario is CostScenario.BASE:
            return self.base, False
        requested = self.low if scenario is CostScenario.LOW else self.high
        if requested is not None:
            return requested, False
        return (self.base, True) if self.base is not None else (None, False)


@dataclass(frozen=True, slots=True)
class RateSnapshot:
    snapshot_id: str
    data_version: str
    rates: tuple[RateRecord, ...]

    def __post_init__(self) -> None:
        ids = [rate.rate_id for rate in self.rates]
        if len(ids) != len(set(ids)):
            raise ValueError("rate ids must be unique within a snapshot")

    def by_id(self) -> dict[str, RateRecord]:
        return {rate.rate_id: rate for rate in self.rates}


@dataclass(frozen=True, slots=True)
class CostPolicy:
    preliminaries_rate: Decimal = Decimal("0")
    ohp_rate: Decimal = Decimal("0")
    contingency_rate: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0.07")
    currency: str = "THB"
    rounding_quantum: Decimal = Decimal("0.01")

    def __post_init__(self) -> None:
        for field_name in (
            "preliminaries_rate",
            "ohp_rate",
            "contingency_rate",
            "vat_rate",
        ):
            value = require_non_negative(getattr(self, field_name), field_name)
            if value > 1:
                raise ValueError(f"{field_name} must be expressed as a fraction from 0 to 1")
            object.__setattr__(self, field_name, value)
        quantum = as_decimal(self.rounding_quantum, "rounding_quantum")
        if quantum <= 0:
            raise ValueError("rounding_quantum must be greater than zero")
        object.__setattr__(self, "rounding_quantum", quantum)
        if self.currency != "THB":
            raise ValueError("v1 costing supports THB only")


@dataclass(frozen=True, slots=True)
class CostLineResult:
    line_id: str
    description_th: str
    description_en: str
    category: str
    quantity: Decimal
    unit: str
    cost_status: CostStatus
    included: bool
    rate_id: str | None
    low_unit_cost: Decimal
    base_unit_cost: Decimal
    high_unit_cost: Decimal
    low_amount: Decimal
    base_amount: Decimal
    high_amount: Decimal
    pricing_source: str


@dataclass(frozen=True, slots=True)
class ScenarioTotals:
    scenario: CostScenario
    direct_cost: Decimal
    preliminaries: Decimal
    ohp: Decimal
    contingency: Decimal
    subtotal_before_vat: Decimal
    vat: Decimal
    grand_total: Decimal


@dataclass(frozen=True, slots=True)
class CostRevision:
    revision_id: str
    boq_revision_id: str
    rate_snapshot_id: str
    policy: CostPolicy
    lines: tuple[CostLineResult, ...]
    totals: tuple[ScenarioTotals, ...]
    findings: tuple[Finding, ...] = ()

    def total_for(self, scenario: CostScenario) -> ScenarioTotals:
        for total in self.totals:
            if total.scenario is scenario:
                return total
        raise KeyError(scenario)
