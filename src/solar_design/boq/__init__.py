"""Deterministic bill-of-quantities generation and revision handling."""

from .catalogue import (
    boq_template_from_records,
    boq_template_from_snapshot,
    boq_template_item_from_record,
)
from .deltas import apply_boq_deltas
from .generator import QuantityRuleRegistry, generate_boq, generate_boq_baseline
from .models import (
    BOQBaseline,
    BOQDelta,
    BOQDeltaOperation,
    BOQLine,
    BOQRevision,
    BOQTemplate,
    BOQTemplateItem,
    CostStatus,
    LinePrice,
    PriceComponents,
    PricingMode,
)
from .validation import find_duplicate_scopes

__all__ = [
    "BOQBaseline",
    "BOQDelta",
    "BOQDeltaOperation",
    "BOQLine",
    "BOQRevision",
    "BOQTemplate",
    "BOQTemplateItem",
    "CostStatus",
    "LinePrice",
    "PriceComponents",
    "PricingMode",
    "QuantityRuleRegistry",
    "apply_boq_deltas",
    "find_duplicate_scopes",
    "generate_boq",
    "generate_boq_baseline",
    "boq_template_from_records",
    "boq_template_from_snapshot",
    "boq_template_item_from_record",
]
