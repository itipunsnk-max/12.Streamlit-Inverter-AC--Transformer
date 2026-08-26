"""Phase 9 canonical JSON, Excel, and CSV export/import tests."""

from __future__ import annotations

import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

import pytest

from solar_design.boq import BOQLine, BOQRevision, CostStatus, LinePrice, PricingMode
from solar_design.costing import RateRecord, RateSnapshot, calculate_cost
from solar_design.exports import (
    BOQ_CSV_HEADERS,
    COST_CSV_HEADERS,
    ProjectPackage,
    create_project_package,
    export_boq_csv,
    export_cost_csv,
    export_project_excel,
    export_project_json,
    export_records_csv,
    export_reference_csv,
    import_boq_csv,
    import_cost_csv,
    import_project_json,
    import_reference_csv,
    project_package_json_schema,
)
from solar_design.models import ReferenceSnapshot
from solar_design.repositories import ReleaseRepository

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def _package() -> tuple[ReferenceSnapshot, ProjectPackage]:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    line = BOQLine(
        line_id="LINE-TH",
        template_item_id="LINE-TH",
        category="งานติดตั้ง",
        description_th="สายไฟและอุปกรณ์ประกอบ",
        description_en="Cable and accessories",
        quantity=Decimal("1"),
        unit="SET",
        pricing_mode=PricingMode.COMPOSITE,
        cost_status=CostStatus.V,
        rate_id="RATE-TEST",
    )
    boq = BOQRevision("boq-rev-9", "boq-base-9", "run-9", (line,))
    cost = calculate_cost(
        boq,
        RateSnapshot(
            "rates-9",
            snapshot.data_version,
            (RateRecord("RATE-TEST", base=_price("100000")),),
        ),
    )
    package = create_project_package(
        app_version="0.1.0",
        exported_at="2026-08-27T09:00:00+07:00",
        project={
            "project_name": "โครงการทดสอบส่งออก",
            "override_reason": "ผู้ใช้งานยืนยันข้อมูลหน้างาน",
        },
        reference_snapshot=snapshot,
        design_run={
            "design_run_id": "run-9",
            "warnings": [
                {
                    "code": "DRAFT_SOURCE",
                    "message": "ข้อมูลอ้างอิงอยู่ระหว่างการทบทวน",
                    "severity": "WARNING",
                }
            ],
        },
        boq_revision=boq,
        cost_revision=cost,
        unit_rates=tuple(snapshot.unit_rates),
        transformer_prices=tuple(snapshot.transformer_prices),
        assumptions=(
            {"name": "VAT", "value": "7%", "notes": "อัตราภาษีมูลค่าเพิ่ม"},
        ),
        sources=tuple(snapshot.sources),
    )
    return snapshot, package


def _price(value: str) -> LinePrice:
    return LinePrice(PricingMode.COMPOSITE, composite=Decimal(value))


def test_canonical_json_round_trip_contains_versions_hashes_warnings_overrides_and_reconciliation(
) -> None:
    snapshot, package = _package()

    exported = export_project_json(package)
    payload = json.loads(exported.decode("utf-8"))

    assert payload["schema_version"] == "1.0.0"
    assert payload["data_version"] == snapshot.data_version
    assert payload["hashes"]["reference_files"]["sources.csv"] == (
        snapshot.manifest.files["sources.csv"].sha256
    )
    assert len(payload["hashes"]["reference_snapshot_sha256"]) == 64
    assert any(item["code"] == "DRAFT_SOURCE" for item in payload["warnings"])
    assert any(item["reason"] == "ผู้ใช้งานยืนยันข้อมูลหน้างาน" for item in payload["overrides"])
    assert payload["reconciliation"] == [
        {
            "scenario": "LOW",
            "direct_cost": "100000.00",
            "line_amount_sum": "100000.00",
            "difference": "0.00",
            "status": "OK",
        },
        {
            "scenario": "BASE",
            "direct_cost": "100000.00",
            "line_amount_sum": "100000.00",
            "difference": "0.00",
            "status": "OK",
        },
        {
            "scenario": "HIGH",
            "direct_cost": "100000.00",
            "line_amount_sum": "100000.00",
            "difference": "0.00",
            "status": "OK",
        },
    ]
    assert "โครงการทดสอบส่งออก" in exported.decode("utf-8")
    assert import_project_json(exported).to_payload() == package.to_payload()
    assert export_project_json(package) == exported


def test_project_package_freezes_nested_input_before_any_export() -> None:
    snapshot = ReleaseRepository(RELEASE).load_snapshot()
    project = {"project_name": "ชื่อเดิม"}
    line = BOQLine(
        line_id="LINE-FROZEN",
        template_item_id="LINE-FROZEN",
        category="Test",
        description_th="รายการทดสอบ",
        description_en="Test item",
        quantity=Decimal("0"),
        unit="SET",
        pricing_mode=PricingMode.COMPOSITE,
        cost_status=CostStatus.EXCL,
    )
    package = create_project_package(
        app_version="0.1.0",
        exported_at="2026-08-27T09:00:00+07:00",
        project=project,
        reference_snapshot=snapshot,
        design_run={"design_run_id": "run-frozen"},
        boq_revision=BOQRevision("boq-frozen", "base-frozen", "run-frozen", (line,)),
        cost_revision={"revision_id": "cost-frozen", "lines": [], "totals": []},
    )
    project["project_name"] = "ชื่อที่เปลี่ยนภายหลัง"

    assert package.project["project_name"] == "ชื่อเดิม"
    with pytest.raises(TypeError):
        package.project["project_name"] = "แก้ไข package"  # type: ignore[index]


def test_json_hash_tampering_and_schema_contract_are_rejected() -> None:
    _, package = _package()
    payload = json.loads(export_project_json(package).decode("utf-8"))
    payload["hashes"]["reference_files"]["sources.csv"] = "0" * 64

    with pytest.raises(ValueError, match="hashes"):
        import_project_json(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    payload = json.loads(export_project_json(package).decode("utf-8"))
    payload["reconciliation"][0]["status"] = "CHECK"
    with pytest.raises(ValueError, match="reconciliation"):
        import_project_json(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    schema = project_package_json_schema()
    assert set(schema["required"]) >= {
        "schema_version",
        "data_version",
        "hashes",
        "warnings",
        "overrides",
        "reconciliation",
    }


def test_excel_export_has_exactly_eight_sheets_formulas_reconciliation_and_thai_text() -> None:
    _, package = _package()
    workbook_bytes = export_project_excel(package)

    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as workbook:
        workbook_xml = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet_names = tuple(
            item.attrib["name"]
            for item in workbook_xml.findall("main:sheets/main:sheet", namespace)
        )
        xml_text = "\n".join(
            workbook.read(name).decode("utf-8", errors="ignore")
            for name in workbook.namelist()
            if name.startswith("xl/") and name.endswith(".xml")
        )

    assert sheet_names == (
        "Project Information",
        "Design Calculation",
        "BOQ",
        "Cost Summary",
        "Unit Rates",
        "Transformer Prices",
        "Assumptions",
        "Sources",
    )
    assert "โครงการทดสอบส่งออก" in xml_text
    assert "SUM(" in xml_text
    assert "BOQ Reconciliation" in xml_text


def test_boq_and_cost_csv_round_trip_preserves_thai_text_and_columns() -> None:
    _, package = _package()

    boq_csv = export_boq_csv(package)
    cost_csv = export_cost_csv(package)
    assert boq_csv.startswith(b"\xef\xbb\xbf")
    assert "สายไฟและอุปกรณ์ประกอบ" in boq_csv.decode("utf-8-sig")
    assert "สายไฟและอุปกรณ์ประกอบ" in cost_csv.decode("utf-8-sig")

    boq_records = import_boq_csv(boq_csv)
    cost_records = import_cost_csv(cost_csv)
    assert boq_records[0]["description_th"] == "สายไฟและอุปกรณ์ประกอบ"
    assert cost_records[0]["description_th"] == "สายไฟและอุปกรณ์ประกอบ"
    assert export_records_csv(boq_records, BOQ_CSV_HEADERS) == boq_csv
    assert export_records_csv(cost_records, COST_CSV_HEADERS) == cost_csv


def test_reference_csv_import_requires_exact_schema_and_data_version() -> None:
    snapshot, _ = _package()
    unit_rates_csv = export_reference_csv(snapshot, "unit_rates.csv")

    records = import_reference_csv(
        unit_rates_csv,
        expected_schema_version=snapshot.schema_version,
        expected_data_version=snapshot.data_version,
    )
    assert records
    assert records[0]["data_version"] == snapshot.data_version
    assert any("งาน" in record["description_th"] for record in records)

    with pytest.raises(ValueError, match="data_version"):
        import_reference_csv(
            unit_rates_csv,
            expected_schema_version=snapshot.schema_version,
            expected_data_version="wrong-release",
        )
