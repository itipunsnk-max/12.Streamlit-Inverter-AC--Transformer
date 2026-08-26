"""UTF-8 BOM CSV exports suitable for Thai text and spreadsheet import."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from solar_design.boq import BOQRevision
from solar_design.costing import CostRevision

from .serialization import to_primitive


def export_boq_csv(boq: BOQRevision) -> bytes:
    headers = (
        "line_id",
        "template_item_id",
        "category",
        "description_th",
        "description_en",
        "quantity",
        "unit",
        "pricing_mode",
        "cost_status",
        "include_in_total",
        "rate_id",
        "duplicate_scope_group",
        "scope_tags",
        "included_scope_tags",
        "verification_status",
        "source_ids",
        "notes",
    )
    rows = []
    for line in sorted(boq.lines, key=lambda item: (item.sort_order, item.line_id)):
        value = asdict(line)
        rows.append({header: _csv_value(value.get(header)) for header in headers})
    return export_records_csv(rows, headers)


def export_cost_csv(cost: CostRevision) -> bytes:
    headers = (
        "line_id",
        "category",
        "description_th",
        "description_en",
        "quantity",
        "unit",
        "cost_status",
        "included",
        "rate_id",
        "pricing_source",
        "low_unit_cost",
        "base_unit_cost",
        "high_unit_cost",
        "low_amount",
        "base_amount",
        "high_amount",
    )
    rows = []
    for line in sorted(cost.lines, key=lambda item: item.line_id):
        value = asdict(line)
        rows.append({header: _csv_value(value.get(header)) for header in headers})
    return export_records_csv(rows, headers)


def export_records_csv(
    records: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str] | None = None,
) -> bytes:
    materialized = [dict(to_primitive(record)) for record in records]
    if fieldnames is None:
        fieldnames = tuple(sorted({key for record in materialized for key in record}))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for record in materialized:
        writer.writerow(
            {key: _safe_spreadsheet_text(_csv_value(record.get(key))) for key in fieldnames}
        )
    return output.getvalue().encode("utf-8-sig")


def _csv_value(value: Any) -> Any:
    primitive = to_primitive(value)
    if isinstance(primitive, list):
        return " | ".join(str(item) for item in primitive)
    if isinstance(primitive, dict):
        return " | ".join(f"{key}={primitive[key]}" for key in sorted(primitive))
    if isinstance(value, Decimal):
        return format(value, "f")
    return primitive


def _safe_spreadsheet_text(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
