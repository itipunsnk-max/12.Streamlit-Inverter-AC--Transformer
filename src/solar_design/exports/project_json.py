"""Versioned canonical project package for save/reload and audit reproduction."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from .serialization import canonical_json_bytes, to_primitive

PROJECT_PACKAGE_SCHEMA_VERSION = "1.0.0"
PROJECT_PACKAGE_TYPE = "solar_design_project"
DEFAULT_MAX_PROJECT_BYTES = 10 * 1024 * 1024

_REQUIRED_FIELDS = {
    "package_type",
    "schema_version",
    "data_version",
    "app_version",
    "exported_at",
    "hashes",
    "project",
    "reference_snapshot",
    "design_run",
    "boq_revision",
    "cost_revision",
    "audit_records",
    "unit_rates",
    "transformer_prices",
    "assumptions",
    "sources",
    "metadata",
    "warnings",
    "overrides",
    "reconciliation",
}


@dataclass(frozen=True, slots=True)
class ProjectPackage:
    app_version: str
    exported_at: str
    project: Mapping[str, Any]
    reference_snapshot: Mapping[str, Any]
    design_run: Mapping[str, Any]
    boq_revision: Mapping[str, Any]
    cost_revision: Mapping[str, Any]
    audit_records: tuple[Mapping[str, Any], ...] = ()
    unit_rates: tuple[Mapping[str, Any], ...] = ()
    transformer_prices: tuple[Mapping[str, Any], ...] = ()
    assumptions: tuple[Mapping[str, Any], ...] = ()
    sources: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[Mapping[str, Any], ...] = ()
    overrides: tuple[Mapping[str, Any], ...] = ()
    reconciliation: tuple[Mapping[str, Any], ...] = ()
    data_version: str = ""
    hashes: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = PROJECT_PACKAGE_SCHEMA_VERSION
    package_type: str = PROJECT_PACKAGE_TYPE

    def __post_init__(self) -> None:
        if self.package_type != PROJECT_PACKAGE_TYPE:
            raise ValueError(f"unsupported package_type {self.package_type!r}")
        if self.schema_version != PROJECT_PACKAGE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version {self.schema_version!r}; "
                f"expected {PROJECT_PACKAGE_SCHEMA_VERSION!r}"
            )
        if not self.app_version.strip() or not self.exported_at.strip():
            raise ValueError("app_version and exported_at must not be blank")

        # Normalize and freeze every nested value at package construction.  The
        # export functions therefore read a stable value even when their caller
        # still owns the original mutable dictionaries.
        mapping_fields = (
            "project",
            "reference_snapshot",
            "design_run",
            "boq_revision",
            "cost_revision",
            "metadata",
            "hashes",
        )
        for field_name in mapping_fields:
            value = _freeze(to_primitive(getattr(self, field_name)))
            if not isinstance(value, Mapping):
                raise TypeError(f"{field_name} must serialize to an object")
            object.__setattr__(self, field_name, value)
        sequence_fields = (
            "audit_records",
            "unit_rates",
            "transformer_prices",
            "assumptions",
            "sources",
            "warnings",
            "overrides",
            "reconciliation",
        )
        for field_name in sequence_fields:
            value = tuple(
                _freeze(to_primitive(item)) for item in getattr(self, field_name)
            )
            if not all(isinstance(item, Mapping) for item in value):
                raise TypeError(f"{field_name} must be an array of objects")
            object.__setattr__(self, field_name, value)

        expected_reconciliation = _reconcile_cost(self.cost_revision)
        if not self.reconciliation:
            object.__setattr__(self, "reconciliation", _freeze(expected_reconciliation))
        elif _record_keys(self.reconciliation) != _record_keys(expected_reconciliation):
            raise ValueError("project reconciliation does not match the cost revision")

        snapshot = self.reference_snapshot
        snapshot_schema = snapshot.get("schema_version")
        if snapshot_schema is not None and snapshot_schema != self.schema_version:
            raise ValueError(
                "project schema_version does not match reference_snapshot schema_version"
            )
        snapshot_data_version = snapshot.get("data_version")
        data_version = self.data_version or str(snapshot_data_version or "")
        if not data_version:
            raise ValueError("data_version is required and must come from the reference snapshot")
        if snapshot_data_version is not None and snapshot_data_version != data_version:
            raise ValueError(
                "project data_version does not match reference_snapshot data_version"
            )
        object.__setattr__(self, "data_version", data_version)

        expected_hashes = _snapshot_hashes(snapshot)
        hashes = dict(self.hashes)
        if not hashes:
            hashes = expected_hashes
        if hashes != expected_hashes:
            raise ValueError("project hashes do not match the immutable reference snapshot")
        object.__setattr__(self, "hashes", _freeze(hashes))

    def to_payload(self) -> dict[str, Any]:
        return {
            "package_type": self.package_type,
            "schema_version": self.schema_version,
            "data_version": self.data_version,
            "app_version": self.app_version,
            "exported_at": self.exported_at,
            "hashes": to_primitive(self.hashes),
            "project": to_primitive(self.project),
            "reference_snapshot": to_primitive(self.reference_snapshot),
            "design_run": to_primitive(self.design_run),
            "boq_revision": to_primitive(self.boq_revision),
            "cost_revision": to_primitive(self.cost_revision),
            "audit_records": to_primitive(self.audit_records),
            "unit_rates": to_primitive(self.unit_rates),
            "transformer_prices": to_primitive(self.transformer_prices),
            "assumptions": to_primitive(self.assumptions),
            "sources": to_primitive(self.sources),
            "metadata": to_primitive(self.metadata),
            "warnings": to_primitive(self.warnings),
            "overrides": to_primitive(self.overrides),
            "reconciliation": to_primitive(self.reconciliation),
        }


def create_project_package(
    *,
    app_version: str,
    exported_at: str,
    project: object,
    reference_snapshot: object,
    design_run: object,
    boq_revision: object,
    cost_revision: object,
    audit_records: tuple[object, ...] = (),
    unit_rates: tuple[object, ...] = (),
    transformer_prices: tuple[object, ...] = (),
    assumptions: tuple[object, ...] = (),
    sources: tuple[object, ...] = (),
    metadata: Mapping[str, Any] | None = None,
    warnings: tuple[object, ...] = (),
    overrides: tuple[object, ...] = (),
    reconciliation: tuple[object, ...] = (),
) -> ProjectPackage:
    """Create a package from mappings, dataclasses, enums, or Pydantic models."""

    project_value = _mapping(project, "project")
    snapshot_value = _mapping(reference_snapshot, "reference_snapshot")
    design_run_value = _mapping(design_run, "design_run")
    boq_value = _mapping(boq_revision, "boq_revision")
    cost_value = _mapping(cost_revision, "cost_revision")
    audit_value = _mapping_tuple(audit_records, "audit_records")
    warning_value = _merge_records(
        _mapping_tuple(warnings, "warnings"),
        _findings_from((design_run_value, boq_value, cost_value)),
    )
    override_value = _merge_records(
        _mapping_tuple(overrides, "overrides"),
        _overrides_from((project_value, design_run_value, audit_value)),
    )
    reconciliation_value = _mapping_tuple(reconciliation, "reconciliation")
    if not reconciliation_value:
        reconciliation_value = _reconcile_cost(cost_value)
    unit_rate_value = _mapping_tuple(unit_rates, "unit_rates")
    if not unit_rate_value:
        unit_rate_value = _snapshot_records(snapshot_value, "unit_rates")
    transformer_price_value = _mapping_tuple(transformer_prices, "transformer_prices")
    if not transformer_price_value:
        transformer_price_value = _snapshot_records(snapshot_value, "transformer_prices")
    source_value = _mapping_tuple(sources, "sources")
    if not source_value:
        source_value = _snapshot_records(snapshot_value, "sources")
    hashes = _snapshot_hashes(snapshot_value)
    data_version = str(snapshot_value.get("data_version") or "")
    if not data_version:
        raise ValueError("reference_snapshot must include a non-blank data_version")

    return ProjectPackage(
        app_version=app_version,
        exported_at=exported_at,
        project=project_value,
        reference_snapshot=snapshot_value,
        design_run=design_run_value,
        boq_revision=boq_value,
        cost_revision=cost_value,
        audit_records=audit_value,
        unit_rates=unit_rate_value,
        transformer_prices=transformer_price_value,
        assumptions=_mapping_tuple(assumptions, "assumptions"),
        sources=source_value,
        metadata={} if metadata is None else _mapping(metadata, "metadata"),
        warnings=warning_value,
        overrides=override_value,
        reconciliation=reconciliation_value,
        data_version=data_version,
        hashes=hashes,
    )


def export_project_json(package: ProjectPackage, *, pretty: bool = True) -> bytes:
    return canonical_json_bytes(package.to_payload(), indent=2 if pretty else None)


def import_project_json(
    data: bytes | bytearray | str,
    *,
    max_bytes: int = DEFAULT_MAX_PROJECT_BYTES,
) -> ProjectPackage:
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = bytes(data)
    if len(raw) > max_bytes:
        raise ValueError(f"project JSON exceeds the {max_bytes}-byte limit")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("project file is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("project JSON root must be an object")
    unknown = set(payload) - _REQUIRED_FIELDS
    missing = _REQUIRED_FIELDS - set(payload)
    if unknown:
        raise ValueError(f"unknown top-level project fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing top-level project fields: {sorted(missing)}")
    return ProjectPackage(
        package_type=_text(payload["package_type"], "package_type"),
        schema_version=_text(payload["schema_version"], "schema_version"),
        data_version=_text(payload["data_version"], "data_version"),
        app_version=_text(payload["app_version"], "app_version"),
        exported_at=_text(payload["exported_at"], "exported_at"),
        hashes=_dict(payload["hashes"], "hashes"),
        project=_dict(payload["project"], "project"),
        reference_snapshot=_dict(payload["reference_snapshot"], "reference_snapshot"),
        design_run=_dict(payload["design_run"], "design_run"),
        boq_revision=_dict(payload["boq_revision"], "boq_revision"),
        cost_revision=_dict(payload["cost_revision"], "cost_revision"),
        audit_records=_dict_tuple(payload["audit_records"], "audit_records"),
        unit_rates=_dict_tuple(payload["unit_rates"], "unit_rates"),
        transformer_prices=_dict_tuple(payload["transformer_prices"], "transformer_prices"),
        assumptions=_dict_tuple(payload["assumptions"], "assumptions"),
        sources=_dict_tuple(payload["sources"], "sources"),
        metadata=_dict(payload["metadata"], "metadata"),
        warnings=_dict_tuple(payload["warnings"], "warnings"),
        overrides=_dict_tuple(payload["overrides"], "overrides"),
        reconciliation=_dict_tuple(payload["reconciliation"], "reconciliation"),
    )


def project_package_json_schema() -> dict[str, Any]:
    object_schema = {"type": "object"}
    array_schema = {"type": "array", "items": object_schema}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://pttor.example/schemas/solar-design-project-{PROJECT_PACKAGE_SCHEMA_VERSION}.json",
        "title": "Solar Electrical Design Project Package",
        "type": "object",
        "additionalProperties": False,
        "required": sorted(_REQUIRED_FIELDS),
        "properties": {
            "package_type": {"const": PROJECT_PACKAGE_TYPE},
            "schema_version": {"const": PROJECT_PACKAGE_SCHEMA_VERSION},
            "data_version": {"type": "string", "minLength": 1},
            "app_version": {"type": "string", "minLength": 1},
            "exported_at": {"type": "string", "minLength": 1},
            "hashes": {
                "type": "object",
                "additionalProperties": False,
                "required": ["reference_files", "reference_snapshot_sha256"],
                "properties": {
                    "reference_files": {
                        "type": "object",
                        "additionalProperties": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    },
                    "reference_snapshot_sha256": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$",
                    },
                },
            },
            "project": object_schema,
            "reference_snapshot": object_schema,
            "design_run": object_schema,
            "boq_revision": object_schema,
            "cost_revision": object_schema,
            "audit_records": array_schema,
            "unit_rates": array_schema,
            "transformer_prices": array_schema,
            "assumptions": array_schema,
            "sources": array_schema,
            "metadata": object_schema,
            "warnings": array_schema,
            "overrides": array_schema,
            "reconciliation": array_schema,
        },
    }


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    primitive = to_primitive(value)
    if not isinstance(primitive, dict):
        raise TypeError(f"{field_name} must serialize to an object")
    return primitive


def _mapping_tuple(values: tuple[object, ...], field_name: str) -> tuple[Mapping[str, Any], ...]:
    return tuple(_mapping(value, f"{field_name} item") for value in values)


def _snapshot_records(
    snapshot: Mapping[str, Any], field_name: str
) -> tuple[Mapping[str, Any], ...]:
    records = snapshot.get(field_name, ())
    if not isinstance(records, (tuple, list)):
        return ()
    return tuple(
        _mapping(record, f"reference_snapshot.{field_name} item")
        for record in records
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list, set, frozenset)):
        return tuple(_freeze(item) for item in value)
    return value


def _snapshot_hashes(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    manifest = snapshot.get("manifest")
    files = manifest.get("files") if isinstance(manifest, Mapping) else None
    reference_files: dict[str, str] = {}
    if isinstance(files, Mapping):
        for filename, entry in files.items():
            if not isinstance(entry, Mapping):
                raise ValueError(f"reference manifest entry {filename!r} must be an object")
            digest = entry.get("sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError(f"reference manifest entry {filename!r} has an invalid sha256")
            reference_files[str(filename)] = digest.lower()
    if not reference_files:
        # A package may be created from a reduced snapshot mapping in a unit
        # test, but it still must declare an auditable snapshot hash.
        reference_files = {}
    return {
        "reference_files": dict(sorted(reference_files.items())),
        "reference_snapshot_sha256": sha256(
            canonical_json_bytes(snapshot, indent=None)
        ).hexdigest(),
    }


def _merge_records(
    first: tuple[Mapping[str, Any], ...], second: tuple[Mapping[str, Any], ...]
) -> tuple[Mapping[str, Any], ...]:
    unique: dict[bytes, Mapping[str, Any]] = {}
    for record in (*first, *second):
        unique[canonical_json_bytes(record, indent=None)] = record
    return tuple(unique[key] for key in sorted(unique))


def _record_keys(values: tuple[Mapping[str, Any], ...]) -> tuple[bytes, ...]:
    return tuple(sorted(canonical_json_bytes(value, indent=None) for value in values))


def _findings_from(values: tuple[Mapping[str, Any], ...]) -> tuple[Mapping[str, Any], ...]:
    found: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            if {"code", "message", "severity"} <= set(value):
                found.append(value)
            for item in value.values():
                visit(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                visit(item)

    for value in values:
        visit(value)
    return tuple(found)


def _overrides_from(values: tuple[Any, ...]) -> tuple[Mapping[str, Any], ...]:
    found: list[Mapping[str, Any]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            reason = value.get("override_reason")
            if isinstance(reason, str) and reason.strip():
                record: dict[str, Any] = {"reason": reason.strip(), "path": path}
                for key in ("decision_id", "engine", "verification_status"):
                    if key in value:
                        record[key] = value[key]
                found.append(record)
            for key, item in value.items():
                visit(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    for value in values:
        visit(value, "")
    return tuple(found)


def _reconcile_cost(cost_revision: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    lines = cost_revision.get("lines", ())
    totals = cost_revision.get("totals", ())
    if not isinstance(lines, (tuple, list)) or not isinstance(totals, (tuple, list)):
        return ()
    records: list[Mapping[str, Any]] = []
    for total in totals:
        if not isinstance(total, Mapping):
            continue
        scenario = str(total.get("scenario", ""))
        amount_field = f"{scenario.lower()}_amount"
        line_sum = Decimal("0")
        valid = True
        for line in lines:
            if not isinstance(line, Mapping):
                valid = False
                break
            try:
                line_sum += Decimal(str(line.get(amount_field, "0")))
            except (InvalidOperation, ValueError):
                valid = False
                break
        try:
            direct = Decimal(str(total.get("direct_cost", "0")))
        except (InvalidOperation, ValueError):
            valid = False
            direct = Decimal("0")
        difference = (direct - line_sum).quantize(Decimal("0.01")) if valid else None
        records.append(
            {
                "scenario": scenario,
                "direct_cost": format(direct, "f"),
                "line_amount_sum": format(line_sum, "f"),
                "difference": None if difference is None else format(difference, "f"),
                "status": (
                    "OK"
                    if difference is not None and abs(difference) <= Decimal("0.01")
                    else "CHECK"
                ),
            }
        )
    return tuple(records)


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _dict_tuple(value: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must be an array of objects")
    return tuple(value)
