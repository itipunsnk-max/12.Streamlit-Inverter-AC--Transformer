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

from .project_json import ProjectPackage
from .serialization import to_primitive

BOQ_CSV_HEADERS = (
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

COST_CSV_HEADERS = (
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


def export_boq_csv(boq: BOQRevision | ProjectPackage) -> bytes:
    """Export BOQ lines from an immutable revision or a frozen project package."""

    rows = []
    if isinstance(boq, ProjectPackage):
        records = _payload_records(boq, "boq_revision", "lines")
        rows = [
            {header: _csv_value(record.get(header)) for header in BOQ_CSV_HEADERS}
            for record in sorted(
                records,
                key=lambda item: (
                    int(item.get("sort_order", 0) or 0),
                    str(item.get("line_id", "")),
                ),
            )
        ]
    else:
        for line in sorted(boq.lines, key=lambda item: (item.sort_order, item.line_id)):
            value = asdict(line)
            rows.append({header: _csv_value(value.get(header)) for header in BOQ_CSV_HEADERS})
    return export_records_csv(rows, BOQ_CSV_HEADERS)


def export_cost_csv(cost: CostRevision | ProjectPackage) -> bytes:
    """Export cost lines from an immutable revision or a frozen project package."""

    rows = []
    if isinstance(cost, ProjectPackage):
        records = _payload_records(cost, "cost_revision", "lines")
        rows = [
            {header: _csv_value(record.get(header)) for header in COST_CSV_HEADERS}
            for record in sorted(records, key=lambda item: str(item.get("line_id", "")))
        ]
    else:
        for line in sorted(cost.lines, key=lambda item: item.line_id):
            value = asdict(line)
            rows.append({header: _csv_value(value.get(header)) for header in COST_CSV_HEADERS})
    return export_records_csv(rows, COST_CSV_HEADERS)


def import_boq_csv(data: bytes | bytearray | str) -> tuple[dict[str, str], ...]:
    """Parse a BOQ export, preserving Thai text and the stable CSV columns."""

    return import_records_csv(data, expected_headers=BOQ_CSV_HEADERS)


def import_cost_csv(data: bytes | bytearray | str) -> tuple[dict[str, str], ...]:
    """Parse a cost export, preserving Thai text and the stable CSV columns."""

    return import_records_csv(data, expected_headers=COST_CSV_HEADERS)


def import_records_csv(
    data: bytes | bytearray | str,
    *,
    expected_headers: Sequence[str] | None = None,
    expected_schema_version: str | None = None,
    expected_data_version: str | None = None,
) -> tuple[dict[str, str], ...]:
    """Read strict UTF-8 CSV records without executing spreadsheet formulas.

    Empty physical rows are ignored; rows with only empty cells are also
    ignored.  When version columns are present, callers can require exact
    schema/data versions for reference-data imports.
    """

    text = _csv_text(data)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header_row = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV must contain a header row") from exc
    headers = tuple(item.strip() for item in header_row)
    if not headers or any(not item for item in headers):
        raise ValueError("CSV headers must not be blank")
    if len(headers) != len(set(headers)):
        raise ValueError("CSV headers must be unique")
    if expected_headers is not None and headers != tuple(expected_headers):
        raise ValueError(
            f"CSV headers do not match expected columns: {headers!r} != {tuple(expected_headers)!r}"
        )

    records: list[dict[str, str]] = []
    for line_number, values in enumerate(reader, start=2):
        if not values or all(not value.strip() for value in values):
            continue
        if len(values) != len(headers):
            raise ValueError(
                f"CSV row {line_number} has {len(values)} values; expected {len(headers)}"
            )
        record = {
            header: _restore_spreadsheet_text(value)
            for header, value in zip(headers, values, strict=True)
        }
        _validate_expected_version(record, "schema_version", expected_schema_version)
        _validate_expected_version(record, "data_version", expected_data_version)
        records.append(record)
    return tuple(records)


def export_reference_csv(
    snapshot: Mapping[str, Any] | object,
    dataset: str,
) -> bytes:
    """Export one dataset from a pinned snapshot for controlled interchange."""

    payload = to_primitive(snapshot)
    if not isinstance(payload, Mapping):
        raise TypeError("snapshot must serialize to an object")
    normalized = dataset.removesuffix(".csv")
    records = payload.get(normalized)
    if not isinstance(records, (tuple, list)) or not all(
        isinstance(item, Mapping) for item in records
    ):
        raise ValueError(f"snapshot does not contain dataset {dataset!r}")
    materialized = [dict(item) for item in records]
    fieldnames = tuple(
        sorted({str(key) for record in materialized for key in record})
    )
    if not fieldnames:
        raise ValueError(f"dataset {dataset!r} has no columns")
    return export_records_csv(materialized, fieldnames)


def import_reference_csv(
    data: bytes | bytearray | str,
    *,
    expected_schema_version: str,
    expected_data_version: str,
) -> tuple[dict[str, str], ...]:
    """Import a reference CSV while requiring its schema and data versions."""

    return import_records_csv(
        data,
        expected_schema_version=expected_schema_version,
        expected_data_version=expected_data_version,
    )


def export_records_csv(
    records: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str] | None = None,
) -> bytes:
    materialized = [dict(to_primitive(record)) for record in records]
    if fieldnames is None:
        fieldnames = tuple(sorted({key for record in materialized for key in record}))
    else:
        fieldnames = tuple(fieldnames)
    if not fieldnames:
        raise ValueError("CSV export requires at least one field name")
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


def _payload_records(
    package: ProjectPackage,
    container: str,
    field: str,
) -> list[Mapping[str, Any]]:
    payload = package.to_payload()
    value = payload.get(container, {})
    records = value.get(field, []) if isinstance(value, Mapping) else []
    if not isinstance(records, list):
        return []
    return [item for item in records if isinstance(item, Mapping)]


def _csv_text(data: bytes | bytearray | str) -> str:
    if isinstance(data, str):
        return data
    try:
        return bytes(data).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be valid UTF-8 text") from exc


def _restore_spreadsheet_text(value: str) -> str:
    if len(value) >= 2 and value.startswith("'") and value[1] in "=+-@":
        return value[1:]
    return value


def _validate_expected_version(
    record: Mapping[str, str],
    field_name: str,
    expected: str | None,
) -> None:
    if expected is None:
        return
    actual = record.get(field_name)
    if actual != expected:
        raise ValueError(f"CSV {field_name} {actual!r} does not match expected {expected!r}")


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
