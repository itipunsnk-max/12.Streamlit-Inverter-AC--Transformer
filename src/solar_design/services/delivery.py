"""One-call budget delivery orchestration without UI or filesystem dependencies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from solar_design.boq import BOQDelta, BOQRevision, BOQTemplate, QuantityRuleRegistry, generate_boq
from solar_design.costing import CostPolicy, CostRevision, RateSnapshot, calculate_cost
from solar_design.exports import (
    ProjectPackage,
    create_project_package,
    export_boq_csv,
    export_cost_csv,
    export_project_excel,
    export_project_json,
)


@dataclass(frozen=True, slots=True)
class BudgetDelivery:
    boq_revision: BOQRevision
    cost_revision: CostRevision
    project_package: ProjectPackage
    project_json: bytes
    boq_csv: bytes
    cost_csv: bytes
    excel_workbook: bytes


def build_budget_delivery(
    *,
    app_version: str,
    exported_at: str,
    project: object,
    reference_snapshot: object,
    design_run: Mapping[str, Any] | object,
    boq_template: BOQTemplate,
    rate_snapshot: RateSnapshot,
    cost_policy: CostPolicy | None = None,
    boq_deltas: tuple[BOQDelta, ...] = (),
    quantity_rules: QuantityRuleRegistry | None = None,
    audit_records: tuple[object, ...] = (),
    transformer_prices: tuple[object, ...] = (),
    assumptions: tuple[object, ...] = (),
    sources: tuple[object, ...] = (),
    metadata: Mapping[str, Any] | None = None,
) -> BudgetDelivery:
    """Build immutable revisions and every v1 download payload from one snapshot."""

    boq_revision = generate_boq(
        design_run,
        boq_template,
        deltas=boq_deltas,
        quantity_rules=quantity_rules,
    )
    cost_revision = calculate_cost(boq_revision, rate_snapshot, cost_policy)
    package = create_project_package(
        app_version=app_version,
        exported_at=exported_at,
        project=project,
        reference_snapshot=reference_snapshot,
        design_run=design_run,
        boq_revision=boq_revision,
        cost_revision=cost_revision,
        audit_records=audit_records,
        unit_rates=rate_snapshot.rates,
        transformer_prices=transformer_prices,
        assumptions=assumptions,
        sources=sources,
        metadata=metadata,
    )
    return BudgetDelivery(
        boq_revision=boq_revision,
        cost_revision=cost_revision,
        project_package=package,
        project_json=export_project_json(package),
        boq_csv=export_boq_csv(boq_revision),
        cost_csv=export_cost_csv(cost_revision),
        excel_workbook=export_project_excel(package),
    )
