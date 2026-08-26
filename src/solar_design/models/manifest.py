"""Pydantic models for immutable data-release manifests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from solar_design.domain import VerificationStatus

from .schemas import CURRENT_SCHEMA_VERSION


class ReleaseStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class DatasetManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    filename: str = Field(min_length=1)
    schema_version: str = CURRENT_SCHEMA_VERSION
    record_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    schema_version: str = CURRENT_SCHEMA_VERSION
    data_version: str = Field(min_length=1)
    release_status: ReleaseStatus
    release_date: date
    application_compatibility: str = Field(min_length=1)
    allowed_verification_statuses: tuple[str, ...] = Field(min_length=1)
    files: Mapping[str, DatasetManifestEntry]
    source_inventory_count: PositiveInt
    approver_state: str = Field(min_length=1)
    known_limitations: tuple[str, ...] = ()

    @field_validator("files")
    @classmethod
    def validate_files(
        cls, value: Mapping[str, DatasetManifestEntry]
    ) -> Mapping[str, DatasetManifestEntry]:
        if not value:
            raise ValueError("manifest must declare at least one dataset")
        for filename in value:
            if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
                raise ValueError(f"invalid manifest filename: {filename!r}")
        return value

    @field_validator("allowed_verification_statuses")
    @classmethod
    def validate_allowed_statuses(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {status.value for status in VerificationStatus}
        if len(value) != len(set(value)):
            raise ValueError("allowed_verification_statuses must be unique")
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"manifest contains unknown verification statuses: {sorted(unknown)}")
        return value
