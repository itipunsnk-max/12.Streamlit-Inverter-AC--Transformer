"""Immutable BOQ value objects.

The generated baseline is kept separate from user deltas.  Reapplying the same
ordered delta set to the same baseline always produces the same revision id.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from solar_design.domain import Finding, VerificationStatus
from solar_design.validation.numeric import DecimalLike, as_decimal, require_non_negative


class PricingMode(StrEnum):
    COMPOSITE = "COMPOSITE"
    BREAKDOWN = "BREAKDOWN"


class CostStatus(StrEnum):
    F = "F"
    V = "V"
    O = "O"  # noqa: E741 - controlled cost-status code from the source specification
    PS = "PS"
    EXCL = "EXCL"


class BOQDeltaOperation(StrEnum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"


@dataclass(frozen=True, slots=True)
class PriceComponents:
    material: Decimal = Decimal("0")
    labor: Decimal = Decimal("0")
    equipment: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(self, "material", require_non_negative(self.material, "material"))
        object.__setattr__(self, "labor", require_non_negative(self.labor, "labor"))
        object.__setattr__(self, "equipment", require_non_negative(self.equipment, "equipment"))

    @property
    def total(self) -> Decimal:
        return self.material + self.labor + self.equipment


@dataclass(frozen=True, slots=True)
class LinePrice:
    mode: PricingMode
    composite: Decimal | None = None
    components: PriceComponents | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, PricingMode):
            raise ValueError("mode must be COMPOSITE or BREAKDOWN")
        if self.mode is PricingMode.COMPOSITE:
            if self.composite is None or self.components is not None:
                raise ValueError("COMPOSITE price requires composite and forbids components")
            object.__setattr__(
                self,
                "composite",
                require_non_negative(self.composite, "composite"),
            )
        elif self.components is None or self.composite is not None:
            raise ValueError("BREAKDOWN price requires components and forbids composite")

    @property
    def unit_cost(self) -> Decimal:
        if self.mode is PricingMode.COMPOSITE:
            assert self.composite is not None
            return self.composite
        assert self.components is not None
        return self.components.total


@dataclass(frozen=True, slots=True)
class BOQLine:
    line_id: str
    template_item_id: str
    category: str
    description_th: str
    description_en: str
    quantity: Decimal
    unit: str
    pricing_mode: PricingMode
    cost_status: CostStatus = CostStatus.V
    include_in_total: bool = True
    sort_order: int = 0
    rate_id: str | None = None
    price_override: LinePrice | None = None
    provisional_price: LinePrice | None = None
    duplicate_scope_group: str | None = None
    scope_tags: tuple[str, ...] = ()
    included_scope_tags: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.line_id.strip() or not self.template_item_id.strip():
            raise ValueError("line_id and template_item_id must not be blank")
        if not self.category.strip() or not self.unit.strip():
            raise ValueError("category and unit must not be blank")
        object.__setattr__(self, "quantity", require_non_negative(self.quantity, "quantity"))
        object.__setattr__(self, "scope_tags", _normalized_tokens(self.scope_tags))
        object.__setattr__(
            self, "included_scope_tags", _normalized_tokens(self.included_scope_tags)
        )
        object.__setattr__(self, "source_ids", tuple(sorted(set(self.source_ids))))
        if self.price_override is not None and self.price_override.mode is not self.pricing_mode:
            raise ValueError("price_override mode must match line pricing_mode")
        if (
            self.provisional_price is not None
            and self.provisional_price.mode is not self.pricing_mode
        ):
            raise ValueError("provisional_price mode must match line pricing_mode")
        if self.price_override is not None and self.provisional_price is not None:
            raise ValueError("a BOQ line must not have both price_override and provisional_price")
        if self.cost_status is CostStatus.EXCL:
            object.__setattr__(self, "include_in_total", False)

    @property
    def is_effectively_included(self) -> bool:
        return (
            self.include_in_total and self.cost_status is not CostStatus.EXCL and self.quantity > 0
            and (
                self.cost_status is not CostStatus.PS
                or self.price_override is not None
                or self.provisional_price is not None
            )
        )


@dataclass(frozen=True, slots=True)
class BOQTemplateItem:
    item_id: str
    category: str
    description_th: str
    description_en: str
    unit: str
    pricing_mode: PricingMode
    quantity_rule_key: str
    quantity_parameters: Mapping[str, Any] = field(default_factory=dict)
    conditions: Mapping[str, Any] = field(default_factory=dict)
    cost_status: CostStatus = CostStatus.V
    include_in_total: bool = True
    sort_order: int = 0
    rate_id: str | None = None
    duplicate_scope_group: str | None = None
    scope_tags: tuple[str, ...] = ()
    included_scope_tags: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.item_id.strip() or not self.quantity_rule_key.strip():
            raise ValueError("template item id and quantity rule key must not be blank")


@dataclass(frozen=True, slots=True)
class BOQTemplate:
    template_id: str
    revision: str
    installation_type: str
    items: tuple[BOQTemplateItem, ...]

    def __post_init__(self) -> None:
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("BOQ template item ids must be unique")


@dataclass(frozen=True, slots=True)
class BOQBaseline:
    baseline_id: str
    design_run_id: str
    template_id: str
    template_revision: str
    lines: tuple[BOQLine, ...]

    def __post_init__(self) -> None:
        _validate_unique_line_ids(self.lines)


@dataclass(frozen=True, slots=True)
class BOQDelta:
    delta_id: str
    sequence: int
    operation: BOQDeltaOperation
    target_line_id: str
    reason: str
    changes: Mapping[str, Any] = field(default_factory=dict)
    added_line: BOQLine | None = None

    def __post_init__(self) -> None:
        if not self.delta_id.strip() or not self.target_line_id.strip():
            raise ValueError("delta_id and target_line_id must not be blank")
        if self.sequence < 1:
            raise ValueError("delta sequence must be at least 1")
        if not self.reason.strip():
            raise ValueError("BOQ delta reason must not be blank")
        if self.operation is BOQDeltaOperation.ADD:
            if self.added_line is None or self.added_line.line_id != self.target_line_id:
                raise ValueError("ADD delta requires an added_line matching target_line_id")
            if self.changes:
                raise ValueError("ADD delta must not contain changes")
        elif self.added_line is not None:
            raise ValueError("only ADD deltas may contain added_line")
        if self.operation is BOQDeltaOperation.UPDATE and not self.changes:
            raise ValueError("UPDATE delta requires at least one changed field")


@dataclass(frozen=True, slots=True)
class BOQRevision:
    revision_id: str
    baseline_id: str
    design_run_id: str
    lines: tuple[BOQLine, ...]
    deltas: tuple[BOQDelta, ...] = ()
    findings: tuple[Finding, ...] = ()

    def __post_init__(self) -> None:
        _validate_unique_line_ids(self.lines)


def _normalized_tokens(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value.strip().lower() for value in values if value.strip()}))


def _validate_unique_line_ids(lines: tuple[BOQLine, ...]) -> None:
    ids = [line.line_id for line in lines]
    if len(ids) != len(set(ids)):
        raise ValueError("BOQ line ids must be unique")


def decimal_or_none(value: DecimalLike | None) -> Decimal | None:
    return None if value is None else as_decimal(value, "value")
