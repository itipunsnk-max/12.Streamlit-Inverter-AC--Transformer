"""Phase 7 tests for Decimal costing, fallback policy, and reconciliation."""

from __future__ import annotations

from decimal import Decimal

from solar_design.boq import (
    BOQLine,
    BOQRevision,
    CostStatus,
    LinePrice,
    PriceComponents,
    PricingMode,
)
from solar_design.costing import (
    CostPolicy,
    CostScenario,
    RateRecord,
    RateSnapshot,
    calculate_cost,
)
from solar_design.domain import FindingSeverity


def _price(value: str, mode: PricingMode = PricingMode.COMPOSITE) -> LinePrice:
    if mode is PricingMode.COMPOSITE:
        return LinePrice(mode, composite=Decimal(value))
    return LinePrice(
        mode,
        components=PriceComponents(material=Decimal(value), labor=Decimal("0")),
    )


def _line(
    line_id: str,
    *,
    rate_id: str | None = "RATE-1",
    quantity: str = "1",
    mode: PricingMode = PricingMode.COMPOSITE,
    status: CostStatus = CostStatus.V,
    include_in_total: bool = True,
) -> BOQLine:
    return BOQLine(
        line_id=line_id,
        template_item_id=line_id,
        category="Test",
        description_th=line_id,
        description_en=line_id,
        quantity=Decimal(quantity),
        unit="SET",
        pricing_mode=mode,
        cost_status=status,
        include_in_total=include_in_total,
        rate_id=rate_id,
    )


def _boq(*lines: BOQLine) -> BOQRevision:
    return BOQRevision("boq-rev-1", "boq-base-1", "run-1", tuple(lines))


def _snapshot(*rates: RateRecord) -> RateSnapshot:
    return RateSnapshot("rates-1", "2026.08-draft", tuple(rates))


def test_sequential_waterfall_reconciles_100000_baht_example() -> None:
    boq = _boq(_line("direct"))
    rates = _snapshot(RateRecord("RATE-1", base=_price("100000")))
    policy = CostPolicy(
        preliminaries_rate=Decimal("0.05"),
        ohp_rate=Decimal("0.10"),
        contingency_rate=Decimal("0.05"),
        vat_rate=Decimal("0.07"),
    )

    result = calculate_cost(boq, rates, policy)
    total = result.total_for(CostScenario.BASE)

    assert total.direct_cost == Decimal("100000.00")
    assert total.preliminaries == Decimal("5000.00")
    assert total.ohp == Decimal("10500.00")
    assert total.contingency == Decimal("5775.00")
    assert total.subtotal_before_vat == Decimal("121275.00")
    assert total.vat == Decimal("8489.25")
    assert total.grand_total == Decimal("129764.25")


def test_low_base_high_use_distinct_prices_and_reconcile_each_scenario() -> None:
    boq = _boq(_line("direct"))
    rates = _snapshot(
        RateRecord(
            "RATE-1",
            base=_price("100000"),
            low=_price("90000"),
            high=_price("110000"),
        )
    )
    policy = CostPolicy(
        preliminaries_rate=Decimal("0.05"),
        ohp_rate=Decimal("0.10"),
        contingency_rate=Decimal("0.05"),
        vat_rate=Decimal("0.07"),
    )

    result = calculate_cost(boq, rates, policy)

    assert result.total_for(CostScenario.LOW).grand_total == Decimal("116787.83")
    assert result.total_for(CostScenario.BASE).grand_total == Decimal("129764.25")
    assert result.total_for(CostScenario.HIGH).grand_total == Decimal("142740.68")
    assert result.lines[0].low_amount == Decimal("90000.00")
    assert result.lines[0].base_amount == Decimal("100000.00")
    assert result.lines[0].high_amount == Decimal("110000.00")

    for scenario, field in (
        (CostScenario.LOW, "low_amount"),
        (CostScenario.BASE, "base_amount"),
        (CostScenario.HIGH, "high_amount"),
    ):
        total = result.total_for(scenario)
        assert total.direct_cost == sum(
            (getattr(line, field) for line in result.lines), Decimal("0.00")
        )
        assert total.subtotal_before_vat == sum(
            (total.direct_cost, total.preliminaries, total.ohp, total.contingency),
            Decimal("0.00"),
        )
        assert total.grand_total == total.subtotal_before_vat + total.vat


def test_missing_low_and_high_reuse_base_with_single_point_warning() -> None:
    boq = _boq(_line("single-point"))
    rates = _snapshot(RateRecord("RATE-1", base=_price("1250")))

    result = calculate_cost(boq, rates)

    assert result.lines[0].pricing_source == "RATE:RATE-1"
    assert result.lines[0].low_unit_cost == Decimal("1250.00")
    assert result.lines[0].high_unit_cost == Decimal("1250.00")
    assert [item.code for item in result.findings].count("SINGLE_POINT_PRICE") == 2
    assert all(
        item.severity is FindingSeverity.WARNING
        for item in result.findings
        if item.code == "SINGLE_POINT_PRICE"
    )


def test_missing_base_price_is_review_and_never_silently_included() -> None:
    boq = _boq(_line("missing-base"))
    rates = _snapshot(RateRecord("RATE-1", base=None, low=_price("900"), high=_price("1100")))

    result = calculate_cost(boq, rates)

    assert result.lines[0].included is False
    assert result.lines[0].pricing_source == "MISSING_BASE_PRICE"
    assert result.total_for(CostScenario.BASE).direct_cost == Decimal("0.00")
    finding = next(item for item in result.findings if item.code == "MISSING_BASE_PRICE")
    assert finding.severity is FindingSeverity.REVIEW


def test_rounding_is_decimal_half_up_for_unit_line_and_waterfall_layers() -> None:
    boq = _boq(_line("rounded", quantity="3"))
    rates = _snapshot(RateRecord("RATE-1", base=_price("0.005")))
    policy = CostPolicy(
        preliminaries_rate=Decimal("0.005"),
        ohp_rate=Decimal("0.005"),
        contingency_rate=Decimal("0.005"),
        vat_rate=Decimal("0.005"),
    )

    result = calculate_cost(boq, rates, policy)
    total = result.total_for(CostScenario.BASE)

    assert result.lines[0].base_unit_cost == Decimal("0.01")
    assert result.lines[0].base_amount == Decimal("0.03")
    assert total.direct_cost == Decimal("0.03")
    assert total.preliminaries == Decimal("0.00")
    assert total.ohp == Decimal("0.00")
    assert total.contingency == Decimal("0.00")
    assert total.vat == Decimal("0.00")
    assert total.grand_total == Decimal("0.03")


def test_breakdown_cost_uses_component_total_once() -> None:
    boq = _boq(_line("breakdown", mode=PricingMode.BREAKDOWN))
    rates = _snapshot(
        RateRecord(
            "RATE-1",
            base=LinePrice(
                PricingMode.BREAKDOWN,
                components=PriceComponents(
                    material=Decimal("40"), labor=Decimal("30"), equipment=Decimal("5")
                ),
            ),
        )
    )

    result = calculate_cost(boq, rates)

    assert result.lines[0].base_unit_cost == Decimal("75.00")
    assert result.total_for(CostScenario.BASE).direct_cost == Decimal("75.00")


def test_rate_price_modes_must_match_line_mode() -> None:
    boq = _boq(_line("mismatch", mode=PricingMode.BREAKDOWN))
    rates = _snapshot(RateRecord("RATE-1", base=_price("100")))

    result = calculate_cost(boq, rates)

    assert result.lines[0].included is False
    finding = next(item for item in result.findings if item.code == "PRICE_MODE_MISMATCH")
    assert finding.severity is FindingSeverity.BLOCKER
