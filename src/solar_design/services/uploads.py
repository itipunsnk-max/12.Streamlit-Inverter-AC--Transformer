"""Boundary validation for project JSON and reviewed master-data CSV uploads."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from dataclasses import dataclass

from solar_design.exports import ProjectPackage, import_project_json

_JSON_MIME_TYPES = {"application/json", "text/json", "application/octet-stream", ""}
_CSV_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "",
}


@dataclass(frozen=True, slots=True)
class UploadedTable:
    fieldnames: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]


def load_project_upload(
    *,
    filename: str,
    mime_type: str | None,
    data: bytes,
    max_bytes: int = 10 * 1024 * 1024,
) -> ProjectPackage:
    _validate_upload_metadata(
        filename=filename,
        mime_type=mime_type,
        data=data,
        extension=".json",
        allowed_mime_types=_JSON_MIME_TYPES,
        max_bytes=max_bytes,
    )
    return import_project_json(data, max_bytes=max_bytes)


def load_tabular_upload(
    *,
    filename: str,
    mime_type: str | None,
    data: bytes,
    required_fields: tuple[str, ...],
    allowed_fields: tuple[str, ...],
    max_bytes: int = 5 * 1024 * 1024,
    max_rows: int = 50_000,
) -> UploadedTable:
    """Load strict UTF-8 CSV and reject missing, duplicate, or unknown columns."""

    _validate_upload_metadata(
        filename=filename,
        mime_type=mime_type,
        data=data,
        extension=".csv",
        allowed_mime_types=_CSV_MIME_TYPES,
        max_bytes=max_bytes,
    )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("master-data CSV must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise ValueError("master-data CSV has no header row")
    normalized = tuple(name.strip() for name in reader.fieldnames)
    if any(not name for name in normalized):
        raise ValueError("master-data CSV contains a blank column name")
    if len(normalized) != len(set(normalized)):
        raise ValueError("master-data CSV contains duplicate column names")
    unknown = set(normalized) - set(allowed_fields)
    missing = set(required_fields) - set(normalized)
    if unknown:
        raise ValueError(f"unknown master-data fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing required master-data fields: {sorted(missing)}")

    rows: list[Mapping[str, str]] = []
    for index, raw_row in enumerate(reader, start=2):
        if len(rows) >= max_rows:
            raise ValueError(f"master-data CSV exceeds the {max_rows}-row limit")
        if None in raw_row:
            raise ValueError(f"row {index} contains more values than the header")
        row = {key: (value or "").strip() for key, value in raw_row.items()}
        if all(not value for value in row.values()):
            continue
        rows.append(row)
    return UploadedTable(fieldnames=normalized, rows=tuple(rows))


def _validate_upload_metadata(
    *,
    filename: str,
    mime_type: str | None,
    data: bytes,
    extension: str,
    allowed_mime_types: set[str],
    max_bytes: int,
) -> None:
    if not filename.lower().endswith(extension):
        raise ValueError(f"upload filename must end with {extension}")
    normalized_mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if normalized_mime not in allowed_mime_types:
        raise ValueError(f"unsupported upload MIME type {mime_type!r}")
    if not data:
        raise ValueError("upload is empty")
    if len(data) > max_bytes:
        raise ValueError(f"upload exceeds the {max_bytes}-byte limit")
