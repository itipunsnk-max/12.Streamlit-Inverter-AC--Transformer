"""Phase 6 tests for deterministic BOQ generation and user revisions."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from solar_design.boq import (
    BOQDelta,
    BOQDeltaOperation,
    BOQLine,
    BOQTemplate,
    BOQTemplateItem,
    CostStatus,
    LinePrice,
    PriceComponents,
    PricingMode,
    boq_template_from_snapshot,
    find_duplicate_scopes,
    generate_boq,
    generate_boq_baseline,
)
from solar_design.domain import FindingSeverity
from solar_design.repositories import ReleaseRepository

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def _item(
    item_id: str,
    *,
    quantity_rule_key: str = "fixed",
    quantity: str = "1",
    status: CostStatus = CostStatus.V,
    mode: PricingMode = PricingMode.COMPOSITE,
    conditions: dict[str, object] | None = None,
    group: str | None = None,
    scope_tags: tuple[str, ...] = (),
    included_scope_tags: tuple[str, ...] = (),
) -> BOQTemplateItem:
    parameters = (
        {"quantity": Decimal(quantity)}
        if quantity_rule_key == "fixed"
        else {"path": "transformer.count"}
        if quantity_rule_key == "field"
        else {}
    )
    return BOQTemplateItem(
        item_id=item_id,
        category="Test",
        description_th=item_id,
        description_en=item_id,
        unit="SET",
        pricing_mode=mode,
        quantity_rule_key=quantity_rule_key,
        quantity_parameters=parameters,
        conditions=conditions or {"installation_type": "YARD"},
        cost_status=status,
        sort_order=1,
        duplicate_scope_group=group,
        scope_tags=scope_tags,
        included_scope_tags=included_scope_tags,
    )


def _template(*items: BOQTemplateItem) -> BOQTemplate:
    return BOQTemplate("BOQ-TEST", "1", "YARD", tuple(items))


def _line(
    line_id: str,
    *,
    status: CostStatus = CostStatus.V,
    group: str | None = None,
    scope_tags: tuple[str, ...] = (),
    included_scope_tags: tuple[str, ...] = (),
    price: LinePrice | None = None,
    provisional: LinePrice | None = None,
) -> BOQLine:
    selected_price = price if price is not None else provisional
    pricing_mode = selected_price.mode if selected_price is not None else PricingMode.COMPOSITE
    return BOQLine(
        line_id=line_id,
        template_item_id=line_id,
        category="Test",
        description_th=line_id,
        description_en=line_id,
        quantity=Decimal("1"),
        unit="SET",
        pricing_mode=pricing_mode,
        cost_status=status,
        price_override=price,
        provisional_price=provisional,
        duplicate_scope_group=group,
        scope_tags=scope_tags,
        included_scope_tags=included_scope_tags,
    )


def test_baseline_is_deterministic_and_quantity_rules_are_explicit() -> None:
    fixed_item = _item("fixed", quantity="2")
    field_item = BOQTemplateItem(
        item_id="field",
        category="Test",
        description_th="field",
        description_en="field",
        unit="SET",
        pricing_mode=PricingMode.BREAKDOWN,
        quantity_rule_key="field",
        quantity_parameters={"path": "transformer.count", "multiplier": Decimal("2")},
        conditions={"installation_type": "YARD"},
        sort_order=2,
    )
    template = _template(fixed_item, field_item, _item("zero", quantity="0"))
    context = {"design_run_id": "run-1", "installation_type": "YARD", "transformer": {"count": 2}}

    first = generate_boq_baseline(context, template)
    second = generate_boq_baseline(context, template)

    assert first == second
    assert first.baseline_id == second.baseline_id
    assert [line.line_id for line in first.lines] == ["BOQ-TEST:fixed", "BOQ-TEST:field"]
    assert first.lines[0].quantity == Decimal("2")
    assert first.lines[1].quantity == Decimal("4")


def test_regeneration_reapplies_manual_delta_and_is_idempotent() -> None:
    template = _template(_item("manual", quantity_rule_key="field"))
    context = {"design_run_id": "run-1", "installation_type": "YARD", "transformer": {"count": 2}}
    delta = BOQDelta(
        delta_id="manual-quantity",
        sequence=1,
        operation=BOQDeltaOperation.UPDATE,
        target_line_id="BOQ-TEST:manual",
        reason="Owner corrected quantity",
        changes={"quantity": Decimal("9"), "description_en": "Manual description"},
    )

    first = generate_boq(context, template, deltas=(delta,))
    regenerated = generate_boq(
        {**context, "transformer": {"count": 5}},
        template,
        deltas=(delta,),
    )
    repeated = generate_boq(context, template, deltas=(delta, delta))

    assert first.lines[0].quantity == Decimal("9")
    assert regenerated.lines[0].quantity == Decimal("9")
    assert regenerated.lines[0].description_en == "Manual description"
    assert repeated.revision_id == first.revision_id
    assert repeated.lines == first.lines


def test_cost_statuses_and_pricing_modes_do_not_double_count() -> None:
    composite = LinePrice(PricingMode.COMPOSITE, composite=Decimal("100"))
    breakdown = LinePrice(
        PricingMode.BREAKDOWN,
        components=PriceComponents(
            material=Decimal("40"), labor=Decimal("30"), equipment=Decimal("5")
        ),
    )
    assert composite.unit_cost == Decimal("100")
    assert breakdown.unit_cost == Decimal("75")

    assert _line("F", status=CostStatus.F, price=composite).is_effectively_included
    assert _line("V", status=CostStatus.V, price=breakdown).is_effectively_included
    assert _line("O", status=CostStatus.O, price=composite).is_effectively_included
    assert _line("PS", status=CostStatus.PS, provisional=composite).is_effectively_included
    assert not _line("PS-MISSING", status=CostStatus.PS).is_effectively_included
    excluded = _line("EXCL", status=CostStatus.EXCL, price=composite)
    assert not excluded.include_in_total
    assert not excluded.is_effectively_included

    with pytest.raises(ValueError, match="forbids components"):
        LinePrice(PricingMode.COMPOSITE, composite=Decimal("100"), components=PriceComponents())
    with pytest.raises(ValueError, match="forbids composite"):
        LinePrice(
            PricingMode.BREAKDOWN,
            composite=Decimal("100"),
            components=PriceComponents(),
        )
    with pytest.raises(ValueError, match="both price_override"):
        _line("DOUBLE", price=composite, provisional=composite)


def test_duplicate_scope_detection_ignores_excluded_and_unpriced_ps_lines() -> None:
    composite = LinePrice(PricingMode.COMPOSITE, composite=Decimal("100"))
    lines = (
        _line("crane-a", group="crane", price=composite),
        _line("crane-b", group="crane", price=composite),
        _line("includes-transport", included_scope_tags=("transport",), price=composite),
        _line("transport", scope_tags=("transport",), price=composite),
        _line("excluded-crane", status=CostStatus.EXCL, group="crane", price=composite),
        _line("pending-crane", status=CostStatus.PS, group="crane"),
    )

    findings = find_duplicate_scopes(lines)

    assert sum(item.code == "BOQ_DUPLICATE_SCOPE_GROUP" for item in findings) == 1
    assert sum(item.code == "BOQ_INCLUDED_SCOPE_OVERLAP" for item in findings) == 1
    assert all(item.severity is FindingSeverity.WARNING for item in findings)
    assert "excluded-crane" not in " ".join(item.message for item in findings)
    assert "pending-crane" not in " ".join(item.message for item in findings)


def test_release_template_adapter_keeps_statuses_and_generates_deterministic_yard_baseline(
) -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    template = boq_template_from_snapshot(snapshot, installation_type="YARD")
    baseline = generate_boq_baseline(
        {"design_run_id": "release-run", "installation_type": "YARD"},
        template,
    )

    assert template.template_id == "BOQ-YARD"
    assert [line.quantity for line in baseline.lines] == [Decimal("5"), Decimal("1")]
    assert [line.cost_status for line in baseline.lines] == [CostStatus.PS, CostStatus.V]
    assert baseline.lines[0].pricing_mode is PricingMode.COMPOSITE
    assert baseline.lines[1].pricing_mode is PricingMode.COMPOSITE
    assert not baseline.lines[0].is_effectively_included
    assert baseline.lines[1].is_effectively_included
