"""Versioned canonical project package for save/reload and audit reproduction."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .serialization import canonical_json_bytes, to_primitive

PROJECT_PACKAGE_SCHEMA_VERSION = "1.0.0"
PROJECT_PACKAGE_TYPE = "solar_design_project"
DEFAULT_MAX_PROJECT_BYTES = 10 * 1024 * 1024

_REQUIRED_FIELDS = {
    "package_type",
    "schema_version",
    "app_version",
    "exported_at",
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

    def to_payload(self) -> dict[str, Any]:
        return {
            "package_type": self.package_type,
            "schema_version": self.schema_version,
            "app_version": self.app_version,
            "exported_at": self.exported_at,
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
) -> ProjectPackage:
    """Create a package from mappings, dataclasses, enums, or Pydantic models."""

    return ProjectPackage(
        app_version=app_version,
        exported_at=exported_at,
        project=_mapping(project, "project"),
        reference_snapshot=_mapping(reference_snapshot, "reference_snapshot"),
        design_run=_mapping(design_run, "design_run"),
        boq_revision=_mapping(boq_revision, "boq_revision"),
        cost_revision=_mapping(cost_revision, "cost_revision"),
        audit_records=_mapping_tuple(audit_records, "audit_records"),
        unit_rates=_mapping_tuple(unit_rates, "unit_rates"),
        transformer_prices=_mapping_tuple(transformer_prices, "transformer_prices"),
        assumptions=_mapping_tuple(assumptions, "assumptions"),
        sources=_mapping_tuple(sources, "sources"),
        metadata={} if metadata is None else _mapping(metadata, "metadata"),
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
        app_version=_text(payload["app_version"], "app_version"),
        exported_at=_text(payload["exported_at"], "exported_at"),
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
            "app_version": {"type": "string", "minLength": 1},
            "exported_at": {"type": "string", "minLength": 1},
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
        },
    }


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    primitive = to_primitive(value)
    if not isinstance(primitive, dict):
        raise TypeError(f"{field_name} must serialize to an object")
    return primitive


def _mapping_tuple(values: tuple[object, ...], field_name: str) -> tuple[Mapping[str, Any], ...]:
    return tuple(_mapping(value, f"{field_name} item") for value in values)


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
