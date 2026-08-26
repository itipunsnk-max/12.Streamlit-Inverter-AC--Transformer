"""Budgetary cost engine with explicit price provenance and rounding."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from solar_design.boq import BOQLine, BOQRevision, CostStatus, LinePrice
from solar_design.boq.deltas import content_id
from solar_design.domain import Finding, FindingSeverity, VerificationStatus

from .models import (
    CostLineResult,
    CostPolicy,
    CostRevision,
    CostScenario,
    RateRecord,
    RateSnapshot,
    ScenarioTotals,
)


def calculate_cost(
    boq: BOQRevision,
    rates: RateSnapshot,
    policy: CostPolicy | None = None,
) -> CostRevision:
    """Calculate three scenarios using the approved sequential cost waterfall.

    Each unit cost, line amount, and waterfall layer is rounded independently with
    ``ROUND_HALF_UP``.  EXCL lines never enter totals.  PS lines enter totals only
    when they have an explicit provisional price.
    """

    active_policy = policy or CostPolicy()
    rate_by_id = rates.by_id()
    findings: list[Finding] = list(boq.findings)
    cost_lines: list[CostLineResult] = []

    for line in boq.lines:
        scenario_prices, pricing_source, line_findings = _resolve_prices(line, rate_by_id)
        findings.extend(line_findings)
        included = _is_priced(line, scenario_prices)
        unit_costs: dict[CostScenario, Decimal] = {}
        amounts: dict[CostScenario, Decimal] = {}
        for scenario in CostScenario:
            price = scenario_prices.get(scenario)
            unit_cost = Decimal("0") if price is None else _money(price.unit_cost, active_policy)
            amount = (
                _money(line.quantity * unit_cost, active_policy) if included else Decimal("0.00")
            )
            unit_costs[scenario] = unit_cost
            amounts[scenario] = amount
        cost_lines.append(
            CostLineResult(
                line_id=line.line_id,
                description_th=line.description_th,
                description_en=line.description_en,
                category=line.category,
                quantity=line.quantity,
                unit=line.unit,
                cost_status=line.cost_status,
                included=included,
                rate_id=line.rate_id,
                low_unit_cost=unit_costs[CostScenario.LOW],
                base_unit_cost=unit_costs[CostScenario.BASE],
                high_unit_cost=unit_costs[CostScenario.HIGH],
                low_amount=amounts[CostScenario.LOW],
                base_amount=amounts[CostScenario.BASE],
                high_amount=amounts[CostScenario.HIGH],
                pricing_source=pricing_source,
            )
        )

    ordered_lines = tuple(sorted(cost_lines, key=lambda item: item.line_id))
    totals = tuple(
        _calculate_scenario_totals(scenario, ordered_lines, active_policy)
        for scenario in CostScenario
    )
    revision_id = content_id(
        {
            "boq_revision_id": boq.revision_id,
            "rate_snapshot_id": rates.snapshot_id,
            "policy": active_policy,
            "lines": ordered_lines,
            "totals": totals,
        },
        prefix="costrev",
    )
    return CostRevision(
        revision_id=revision_id,
        boq_revision_id=boq.revision_id,
        rate_snapshot_id=rates.snapshot_id,
        policy=active_policy,
        lines=ordered_lines,
        totals=totals,
        findings=tuple(_deduplicate_findings(findings)),
    )


def _resolve_prices(
    line: BOQLine,
    rate_by_id: dict[str, RateRecord],
) -> tuple[dict[CostScenario, LinePrice | None], str, tuple[Finding, ...]]:
    empty: dict[CostScenario, LinePrice | None] = {
        scenario: None for scenario in CostScenario
    }
    if line.cost_status is CostStatus.EXCL or not line.include_in_total or line.quantity == 0:
        return empty, "EXCLUDED", ()

    if line.cost_status is CostStatus.PS:
        if line.provisional_price is None:
            return (
                empty,
                "MISSING_PROVISIONAL",
                (
                    _finding(
                        "PS_MISSING_PROVISIONAL_VALUE",
                        (
                            f"PS line '{line.line_id}' has no provisional value "
                            "and is omitted from totals."
                        ),
                    ),
                ),
            )
        return (
            {scenario: line.provisional_price for scenario in CostScenario},
            "PROVISIONAL_OVERRIDE",
            (_single_point_finding(line.line_id, "provisional price"),),
        )

    if line.price_override is not None:
        return (
            {scenario: line.price_override for scenario in CostScenario},
            "LINE_OVERRIDE",
            (_single_point_finding(line.line_id, "line price override"),),
        )

    if line.rate_id is None or line.rate_id not in rate_by_id:
        return (
            empty,
            "MISSING_RATE",
            (
                _finding(
                    "MISSING_UNIT_RATE",
                    f"Line '{line.line_id}' has no matching unit rate and contributes zero.",
                ),
            ),
        )

    rate = rate_by_id[line.rate_id]
    if rate.base is None:
        return (
            empty,
            "MISSING_BASE_PRICE",
            (
                Finding(
                    code="MISSING_BASE_PRICE",
                    message=(
                        f"Rate '{rate.rate_id}' has no BASE price for line '{line.line_id}'; "
                        "the line is omitted from totals and requires review."
                    ),
                    severity=FindingSeverity.REVIEW,
                    verification_status=VerificationStatus.UNKNOWN,
                    source_ids=rate.source_ids,
                ),
            ),
        )

    if rate.base.mode is not line.pricing_mode:
        return (
            empty,
            "RATE_MODE_MISMATCH",
            (
                Finding(
                    code="PRICE_MODE_MISMATCH",
                    message=(
                        f"Line '{line.line_id}' expects {line.pricing_mode.value}, but rate "
                        f"'{rate.rate_id}' is {rate.base.mode.value}; line contributes zero."
                    ),
                    severity=FindingSeverity.BLOCKER,
                    verification_status=VerificationStatus.UNKNOWN,
                    source_ids=rate.source_ids,
                ),
            ),
        )

    resolved: dict[CostScenario, LinePrice | None] = {}
    findings: list[Finding] = []
    for scenario in CostScenario:
        price, fell_back = rate.price_for(scenario)
        resolved[scenario] = price
        if fell_back:
            findings.append(
                _finding(
                    "SINGLE_POINT_PRICE",
                    f"Rate '{rate.rate_id}' has no {scenario.value} value; BASE is reused.",
                    source_ids=rate.source_ids,
                )
            )
    return resolved, f"RATE:{rate.rate_id}", tuple(findings)


def _is_priced(line: BOQLine, prices: dict[CostScenario, LinePrice | None]) -> bool:
    if not line.is_effectively_included:
        return False
    if line.cost_status is CostStatus.PS and line.provisional_price is None:
        return False
    return prices[CostScenario.BASE] is not None


def _calculate_scenario_totals(
    scenario: CostScenario,
    lines: tuple[CostLineResult, ...],
    policy: CostPolicy,
) -> ScenarioTotals:
    attribute = f"{scenario.value.lower()}_amount"
    direct = _money(sum((getattr(line, attribute) for line in lines), Decimal("0")), policy)
    preliminaries = _money(direct * policy.preliminaries_rate, policy)
    ohp = _money((direct + preliminaries) * policy.ohp_rate, policy)
    contingency = _money(
        (direct + preliminaries + ohp) * policy.contingency_rate,
        policy,
    )
    subtotal = _money(direct + preliminaries + ohp + contingency, policy)
    vat = _money(subtotal * policy.vat_rate, policy)
    grand_total = _money(subtotal + vat, policy)
    return ScenarioTotals(
        scenario=scenario,
        direct_cost=direct,
        preliminaries=preliminaries,
        ohp=ohp,
        contingency=contingency,
        subtotal_before_vat=subtotal,
        vat=vat,
        grand_total=grand_total,
    )


def _money(value: Decimal, policy: CostPolicy) -> Decimal:
    return value.quantize(policy.rounding_quantum, rounding=ROUND_HALF_UP)


def _finding(
    code: str,
    message: str,
    *,
    source_ids: tuple[str, ...] = (),
) -> Finding:
    return Finding(
        code=code,
        message=message,
        severity=FindingSeverity.WARNING,
        verification_status=VerificationStatus.UNKNOWN,
        source_ids=source_ids,
    )


def _single_point_finding(line_id: str, source: str) -> Finding:
    return _finding(
        "SINGLE_POINT_PRICE",
        f"Line '{line_id}' uses one {source} for LOW, BASE, and HIGH scenarios.",
    )


def _deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    by_key: dict[tuple[object, ...], Finding] = {}
    for finding in findings:
        key = (
            finding.code,
            finding.message,
            finding.severity,
            finding.verification_status,
            finding.source_ids,
            finding.field,
        )
        by_key[key] = finding
    return [by_key[key] for key in sorted(by_key, key=lambda item: tuple(str(v) for v in item))]
