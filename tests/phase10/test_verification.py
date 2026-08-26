"""Phase 10 integration, golden, property, contract, and security tests."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from solar_design.boq import BOQLine, BOQRevision, CostStatus, LinePrice, PricingMode
from solar_design.costing import CostScenario, RateRecord, RateSnapshot, calculate_cost
from solar_design.exports import (
    create_project_package,
    export_project_json,
    export_records_csv,
    import_records_csv,
)
from solar_design.repositories import ReleaseRepository
from solar_design.ui.state import WorkspaceCoordinator

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def test_full_workflow_matches_the_default_release_golden_values_and_is_reproducible() -> None:
    coordinator = WorkspaceCoordinator(RELEASE)
    first = coordinator.run_workflow(coordinator.initial_state())
    second = coordinator.run_workflow(coordinator.initial_state())

    assert first.validation_errors == ()
    assert first.reference_snapshot is not None
    assert first.results.inverter is not None
    assert first.results.transformer is not None
    assert first.results.boq is not None
    assert first.results.cost is not None
    assert first.results.inverter.selected_model_id == "INV-SUNGROW-SG36CX-P2"
    assert first.results.transformer.selected_rating_per_unit_kva == Decimal("100")
    assert first.results.cost.total_for(CostScenario.BASE).grand_total == Decimal("8560.00")

    assert first.results == second.results

    package = create_project_package(
        app_version="0.1.0",
        exported_at="2026-08-27T09:00:00+07:00",
        project=first.inputs,
        reference_snapshot=first.reference_snapshot,
        design_run=first.results,
        boq_revision=first.results.boq,
        cost_revision=first.results.cost,
    )
    exported = export_project_json(package)
    payload = json.loads(exported.decode("utf-8"))
    assert payload["data_version"] == "2026.08-draft"
    assert payload["boq_revision"]["revision_id"] == first.results.boq.revision_id
    assert export_project_json(package) == exported


@settings(max_examples=25, deadline=None)
@given(
    quantity=st.decimals(
        min_value=0, max_value=1000, places=2, allow_nan=False, allow_infinity=False
    ),
    unit_price=st.decimals(
        min_value=0,
        max_value=100000,
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_cost_reconciliation_invariants_hold_for_decimal_inputs(
    quantity: Decimal,
    unit_price: Decimal,
) -> None:
    line = BOQLine(
        line_id="PROPERTY-LINE",
        template_item_id="PROPERTY-LINE",
        category="Property",
        description_th="รายการ property",
        description_en="Property item",
        quantity=quantity,
        unit="SET",
        pricing_mode=PricingMode.COMPOSITE,
        cost_status=CostStatus.V,
        rate_id="PROPERTY-RATE",
    )
    result = calculate_cost(
        BOQRevision("property-boq", "property-base", "property-run", (line,)),
        RateSnapshot(
            "property-rates",
            "2026.08-draft",
            (
                RateRecord(
                    "PROPERTY-RATE",
                    base=LinePrice(PricingMode.COMPOSITE, composite=unit_price),
                ),
            ),
        ),
    )
    total = result.total_for(CostScenario.BASE)

    assert total.direct_cost == sum((item.base_amount for item in result.lines), Decimal("0.00"))
    assert total.subtotal_before_vat >= total.direct_cost
    assert total.grand_total >= total.subtotal_before_vat


def test_release_data_contract_is_versioned_hash_linked_and_closed() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    source_ids = {record.source_id for record in snapshot.sources}
    datasets: tuple[tuple[str, tuple[Any, ...]], ...] = (
        ("inverters.csv", snapshot.inverters),
        ("cables.csv", snapshot.cables),
        ("ampacity.csv", snapshot.ampacity),
        ("grouping_factors.csv", snapshot.grouping_factors),
        ("breakers.csv", snapshot.breakers),
        ("conduits.csv", snapshot.conduits),
        ("pe_mapping.csv", snapshot.pe_mapping),
        ("transformers.csv", snapshot.transformers),
        ("transformer_prices.csv", snapshot.transformer_prices),
        ("unit_rates.csv", snapshot.unit_rates),
        ("design_rules.csv", snapshot.design_rules),
        ("boq_templates.csv", snapshot.boq_templates),
    )

    for filename, records in datasets:
        assert len(records) == snapshot.manifest.files[filename].record_count
        assert all(record.schema_version == snapshot.schema_version for record in records)
        assert all(record.data_version == snapshot.data_version for record in records)
        assert all(set(record.source_ids) <= source_ids for record in records)
    assert snapshot.source_hashes == tuple(
        sorted((filename, entry.sha256) for filename, entry in snapshot.manifest.files.items())
    )


def test_csv_formula_safety_is_round_trip_safe_for_thai_text() -> None:
    csv_data = export_records_csv(
        ({"formula": "=1+1", "plus": "+2", "at": "@cell", "thai": "ภาษาไทย"},),
        ("formula", "plus", "at", "thai"),
    )
    csv_text = csv_data.decode("utf-8-sig")
    assert "'=1+1" in csv_text
    assert "'+2" in csv_text
    imported = import_records_csv(csv_data)

    assert imported == (
        {"formula": "=1+1", "plus": "+2", "at": "@cell", "thai": "ภาษาไทย"},
    )


def test_packaging_contract_declares_src_layout_and_versioned_release() -> None:
    import tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "solar-electrical-design-th"
    assert project["requires-python"] == ">=3.11,<3.15"
    assert tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "setuptools"
    ]["package-dir"] == {"": "src"}
    assert (RELEASE / "manifest.json").is_file()
