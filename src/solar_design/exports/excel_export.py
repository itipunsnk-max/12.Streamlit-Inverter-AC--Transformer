"""Professional eight-sheet XLSX export returned as in-memory bytes."""

from __future__ import annotations

import io
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from .project_json import ProjectPackage

SHEET_NAMES = (
    "Project Information",
    "Design Calculation",
    "BOQ",
    "Cost Summary",
    "Unit Rates",
    "Transformer Prices",
    "Assumptions",
    "Sources",
)

DISCLAIMER = (
    "BUDGETARY ESTIMATE — Draft/unknown engineering rules require review by the design "
    "engineer and owning utility before construction or procurement."
)


def export_project_excel(package: ProjectPackage | Mapping[str, Any]) -> bytes:
    """Return an eight-sheet XLSX payload suitable for ``st.download_button``."""

    try:
        import xlsxwriter
    except ImportError as exc:  # pragma: no cover - dependency error is environment-specific
        raise RuntimeError("XlsxWriter is required for Excel export") from exc

    payload = package.to_payload() if isinstance(package, ProjectPackage) else dict(package)
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "remove_timezone": True,
        },
    )
    workbook.set_properties(
        {
            "title": "Solar Electrical Design and Budgetary Cost Estimate",
            "subject": DISCLAIMER,
            "company": "PTTOR",
            "comments": f"Schema version {payload.get('schema_version', 'unknown')}",
        }
    )
    formats = _formats(workbook)

    project_rows = _project_rows(payload)
    _write_table_sheet(
        workbook,
        "Project Information",
        ("Field", "Value"),
        project_rows,
        formats,
        widths=(36, 80),
    )

    design_rows = tuple(_flatten_rows(payload.get("design_run", {})))
    _write_table_sheet(
        workbook,
        "Design Calculation",
        ("Path", "Value"),
        design_rows,
        formats,
        widths=(52, 72),
    )

    boq_total_row, boq_amount_columns = _write_boq_sheet(workbook, payload, formats)
    _write_cost_summary_sheet(
        workbook,
        payload,
        formats,
        boq_total_row=boq_total_row,
        boq_amount_columns=boq_amount_columns,
    )

    _write_mapping_records_sheet(
        workbook,
        "Unit Rates",
        payload.get("unit_rates", []),
        formats,
    )
    _write_mapping_records_sheet(
        workbook,
        "Transformer Prices",
        payload.get("transformer_prices", []),
        formats,
    )
    _write_mapping_records_sheet(
        workbook,
        "Assumptions",
        payload.get("assumptions", []),
        formats,
    )
    _write_mapping_records_sheet(
        workbook,
        "Sources",
        payload.get("sources", []),
        formats,
    )

    workbook.close()
    return output.getvalue()


def _formats(workbook: Any) -> dict[str, Any]:
    return {
        "title": workbook.add_format(
            {
                "font_name": "Tahoma",
                "font_size": 16,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#155E75",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "disclaimer": workbook.add_format(
            {
                "font_name": "Tahoma",
                "font_size": 9,
                "italic": True,
                "font_color": "#7C2D12",
                "bg_color": "#FFEDD5",
                "text_wrap": True,
                "valign": "vcenter",
            }
        ),
        "header": workbook.add_format(
            {
                "font_name": "Tahoma",
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#0F766E",
                "border": 0,
                "bottom": 2,
                "bottom_color": "#134E4A",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),
        "text": workbook.add_format(
            {"font_name": "Tahoma", "font_size": 9, "valign": "top", "text_wrap": True}
        ),
        "number": workbook.add_format(
            {"font_name": "Tahoma", "font_size": 9, "num_format": "#,##0.00", "valign": "top"}
        ),
        "currency": workbook.add_format(
            {"font_name": "Tahoma", "font_size": 9, "num_format": "#,##0.00", "valign": "top"}
        ),
        "total": workbook.add_format(
            {
                "font_name": "Tahoma",
                "font_size": 10,
                "bold": True,
                "num_format": "#,##0.00",
                "top": 2,
                "top_color": "#0F766E",
                "bg_color": "#ECFDF5",
            }
        ),
        "check_ok": workbook.add_format(
            {"font_name": "Tahoma", "font_size": 9, "font_color": "#166534", "bold": True}
        ),
    }


def _write_table_sheet(
    workbook: Any,
    sheet_name: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    formats: Mapping[str, Any],
    *,
    widths: Sequence[int] | None = None,
) -> Any:
    worksheet = workbook.add_worksheet(sheet_name)
    worksheet.hide_gridlines(2)
    worksheet.set_row(0, 26)
    worksheet.merge_range(0, 0, 0, len(headers) - 1, sheet_name, formats["title"])
    worksheet.set_row(1, 34)
    worksheet.merge_range(1, 0, 1, len(headers) - 1, DISCLAIMER, formats["disclaimer"])
    worksheet.write_row(2, 0, headers, formats["header"])
    materialized = list(rows)
    for row_index, row in enumerate(materialized, start=3):
        for col_index, value in enumerate(row):
            _write_value(worksheet, row_index, col_index, value, formats)
    if materialized:
        worksheet.autofilter(2, 0, 2 + len(materialized), len(headers) - 1)
    worksheet.freeze_panes(3, 0)
    for index, width in enumerate(widths or (24,) * len(headers)):
        worksheet.set_column(index, index, min(width, 80))
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)
    worksheet.set_margins(0.35, 0.35, 0.5, 0.5)
    return worksheet


def _write_boq_sheet(
    workbook: Any,
    payload: Mapping[str, Any],
    formats: Mapping[str, Any],
) -> tuple[int, dict[str, str]]:
    headers = (
        "Line ID",
        "Category",
        "Description (TH)",
        "Description (EN)",
        "Quantity",
        "Unit",
        "Status",
        "Included",
        "Pricing Mode",
        "Rate ID",
        "Verification",
        "Pricing Source",
        "Low Amount",
        "Base Amount",
        "High Amount",
    )
    boq_lines = _records(payload.get("boq_revision", {}), "lines")
    cost_lines = {
        str(item.get("line_id", "")): item
        for item in _records(payload.get("cost_revision", {}), "lines")
    }
    rows: list[tuple[Any, ...]] = []
    for line in sorted(
        boq_lines, key=lambda item: (item.get("sort_order", 0), item.get("line_id", ""))
    ):
        cost_line = cost_lines.get(str(line.get("line_id", "")), {})
        rows.append(
            (
                line.get("line_id"),
                line.get("category"),
                line.get("description_th"),
                line.get("description_en"),
                _number(line.get("quantity")),
                line.get("unit"),
                line.get("cost_status"),
                cost_line.get("included", line.get("include_in_total")),
                line.get("pricing_mode"),
                line.get("rate_id"),
                line.get("verification_status"),
                cost_line.get("pricing_source"),
                _number(cost_line.get("low_amount")),
                _number(cost_line.get("base_amount")),
                _number(cost_line.get("high_amount")),
            )
        )
    worksheet = _write_table_sheet(
        workbook,
        "BOQ",
        headers,
        rows,
        formats,
        widths=(24, 20, 36, 34, 12, 10, 10, 10, 15, 20, 18, 22, 16, 16, 16),
    )
    first_excel_row = 4
    last_excel_row = first_excel_row + len(rows) - 1
    total_zero_based = 3 + len(rows)
    worksheet.write(total_zero_based, 11, "Total", formats["total"])
    amount_columns = {"LOW": "M", "BASE": "N", "HIGH": "O"}
    for column_index, scenario in zip((12, 13, 14), ("LOW", "BASE", "HIGH"), strict=True):
        if rows:
            amount_column = amount_columns[scenario]
            formula = (
                f"=SUM({amount_column}{first_excel_row}:"
                f"{amount_column}{last_excel_row})"
            )
        else:
            formula = "=0"
        direct = _cost_direct(payload, scenario)
        worksheet.write_formula(total_zero_based, column_index, formula, formats["total"], direct)
    return total_zero_based + 1, amount_columns


def _write_cost_summary_sheet(
    workbook: Any,
    payload: Mapping[str, Any],
    formats: Mapping[str, Any],
    *,
    boq_total_row: int,
    boq_amount_columns: Mapping[str, str],
) -> None:
    headers = (
        "Scenario",
        "Direct Cost",
        "Preliminaries",
        "OH&P",
        "Contingency",
        "Subtotal before VAT",
        "VAT",
        "Grand Total",
        "BOQ Reconciliation",
    )
    totals = _records(payload.get("cost_revision", {}), "totals")
    ordered = sorted(
        totals, key=lambda item: {"LOW": 0, "BASE": 1, "HIGH": 2}.get(str(item.get("scenario")), 9)
    )
    rows = []
    for total in ordered:
        rows.append(
            (
                total.get("scenario"),
                _number(total.get("direct_cost")),
                _number(total.get("preliminaries")),
                _number(total.get("ohp")),
                _number(total.get("contingency")),
                _number(total.get("subtotal_before_vat")),
                _number(total.get("vat")),
                _number(total.get("grand_total")),
                "",
            )
        )
    worksheet = _write_table_sheet(
        workbook,
        "Cost Summary",
        headers,
        rows,
        formats,
        widths=(14, 18, 18, 18, 18, 22, 16, 20, 22),
    )
    for offset, total in enumerate(ordered):
        row = 3 + offset
        scenario = str(total.get("scenario", "BASE"))
        column = boq_amount_columns.get(scenario, "N")
        formula = f'=IF(ABS(\'BOQ\'!${column}${boq_total_row}-B{row + 1})<0.01,"OK","CHECK")'
        worksheet.write_formula(row, 8, formula, formats["check_ok"], "OK")
        worksheet.set_row(row, 20)


def _write_mapping_records_sheet(
    workbook: Any,
    sheet_name: str,
    value: Any,
    formats: Mapping[str, Any],
) -> None:
    records = value if isinstance(value, list) else []
    if records and all(isinstance(item, Mapping) for item in records):
        headers = tuple(sorted({str(key) for item in records for key in item}))
        rows = tuple(tuple(_display(item.get(key)) for key in headers) for item in records)
    else:
        headers = ("Status", "Detail")
        rows = (("NO_DATA", "No records were included in this project package."),)
    widths = tuple(24 if index == 0 else 30 for index in range(len(headers)))
    _write_table_sheet(workbook, sheet_name, headers, rows, formats, widths=widths)


def _project_rows(payload: Mapping[str, Any]) -> tuple[tuple[Any, Any], ...]:
    rows: list[tuple[Any, Any]] = [
        ("package_type", payload.get("package_type")),
        ("schema_version", payload.get("schema_version")),
        ("app_version", payload.get("app_version")),
        ("exported_at", payload.get("exported_at")),
    ]
    rows.extend(_flatten_rows(payload.get("project", {}), prefix="project"))
    rows.extend(_flatten_rows(payload.get("reference_snapshot", {}), prefix="reference"))
    rows.extend(_flatten_rows(payload.get("metadata", {}), prefix="metadata"))
    return tuple(rows)


def _flatten_rows(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_rows(value[key], path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]"
            yield from _flatten_rows(item, path)
    else:
        yield prefix or "value", _display(value)


def _records(container: Any, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(container, Mapping):
        return []
    value = container.get(field, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _cost_direct(payload: Mapping[str, Any], scenario: str) -> float:
    totals = _records(payload.get("cost_revision", {}), "totals")
    for item in totals:
        if item.get("scenario") == scenario:
            return _number(item.get("direct_cost")) or 0.0
    return 0.0


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return None


def _display(value: Any) -> Any:
    if isinstance(value, Mapping):
        return " | ".join(f"{key}={_display(value[key])}" for key in sorted(value))
    if isinstance(value, list):
        return " | ".join(str(_display(item)) for item in value)
    return value


def _write_value(
    worksheet: Any,
    row: int,
    column: int,
    value: Any,
    formats: Mapping[str, Any],
) -> None:
    if value is None:
        worksheet.write_blank(row, column, None, formats["text"])
    elif isinstance(value, bool):
        worksheet.write_boolean(row, column, value, formats["text"])
    elif isinstance(value, int | float) and not isinstance(value, bool):
        worksheet.write_number(row, column, value, formats["number"])
    else:
        worksheet.write_string(row, column, str(value), formats["text"])
