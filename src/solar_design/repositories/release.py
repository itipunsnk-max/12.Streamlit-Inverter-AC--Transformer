"""Validated access to an immutable reference-data release."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel, ValidationError

from solar_design.models.manifest import ReleaseManifest
from solar_design.models.schemas import (
    DATASET_MODELS,
    AmpacityRecord,
    BOQTemplateRecord,
    BreakerRecord,
    CableRecord,
    ConduitRecord,
    DesignRuleRecord,
    GroupingFactorRecord,
    InverterRecord,
    PEMappingRecord,
    SourceRecord,
    TransformerPriceRecord,
    TransformerRecord,
    UnitRateRecord,
)
from solar_design.models.snapshot import ReferenceSnapshot


class DataReleaseError(ValueError):
    """Raised when reference data is missing, malformed, or has the wrong hash."""


def _canonical_release_bytes(payload: bytes) -> bytes:
    """Hash text datasets with canonical LF endings on every operating system."""

    return payload.replace(b"\r\n", b"\n")


RecordModel = TypeVar("RecordModel", bound=BaseModel)


class ReleaseRepository:
    """Read, validate, and snapshot one versioned release.

    Calculation engines receive only the resulting ``ReferenceSnapshot`` and
    never access filesystem paths, CSV text, or mutable loader state.
    """

    def __init__(self, release_dir: str | Path) -> None:
        self.release_dir = Path(release_dir).resolve()
        if not self.release_dir.is_dir():
            raise DataReleaseError(f"Release directory does not exist: {self.release_dir}")
        self.manifest = self._load_manifest()
        if self.manifest.data_version != self.release_dir.name:
            raise DataReleaseError(
                "Manifest data_version does not match release directory: "
                f"{self.manifest.data_version!r} != {self.release_dir.name!r}"
            )

    @property
    def data_version(self) -> str:
        return self.manifest.data_version

    def _load_manifest(self) -> ReleaseManifest:
        path = self.release_dir / "manifest.json"
        if not path.is_file():
            raise DataReleaseError(f"Missing release manifest: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ReleaseManifest.model_validate(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            raise DataReleaseError(f"Invalid release manifest: {exc}") from exc

    def _resolve_dataset(self, filename: str) -> Path:
        requested = Path(filename)
        if requested.is_absolute() or len(requested.parts) != 1 or requested.name != filename:
            raise DataReleaseError(f"Dataset filename must be a simple file name: {filename!r}")
        path = (self.release_dir / filename).resolve()
        if path.parent != self.release_dir or not path.is_file():
            raise DataReleaseError(f"Dataset is not available in this release: {filename}")
        return path

    def load_csv(self, filename: str) -> list[dict[str, str | None]]:
        """Load one manifest-declared CSV with strict headers and row widths."""

        path = self._resolve_dataset(filename)
        self._verify_declared_hash(filename, path)
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, strict=True)
                header = next(reader, None)
                if not header:
                    raise DataReleaseError(f"Dataset has no header: {filename}")
                normalized_header = [column.strip() for column in header]
                if any(not column for column in normalized_header):
                    raise DataReleaseError(f"Dataset has a blank header: {filename}")
                if len(normalized_header) != len(set(normalized_header)):
                    raise DataReleaseError(f"Dataset has duplicate headers: {filename}")
                rows: list[dict[str, str | None]] = []
                for line_number, values in enumerate(reader, start=2):
                    if len(values) != len(normalized_header):
                        raise DataReleaseError(
                            f"Dataset {filename} row {line_number} has {len(values)} values; "
                            f"expected {len(normalized_header)}"
                        )
                    rows.append(
                        {
                            column: value.strip() or None
                            for column, value in zip(normalized_header, values, strict=True)
                        }
                    )
                return rows
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            raise DataReleaseError(f"Cannot read dataset {filename}: {exc}") from exc

    def load_dataset(self, filename: str, model: type[RecordModel]) -> tuple[RecordModel, ...]:
        """Validate every row against a frozen Pydantic schema."""

        rows = self.load_csv(filename)
        entry = self.manifest.files.get(filename)
        if entry is None:
            raise DataReleaseError(f"Dataset is not declared by manifest: {filename}")
        if len(rows) != entry.record_count:
            raise DataReleaseError(
                f"Dataset {filename} has {len(rows)} rows; manifest declares {entry.record_count}"
            )
        validated: list[RecordModel] = []
        for row_number, row in enumerate(rows, start=2):
            try:
                record = model.model_validate(row)
            except ValidationError as exc:
                raise DataReleaseError(f"Invalid {filename} row {row_number}: {exc}") from exc
            self._validate_record_identity(filename, record)
            validated.append(record)
        self._validate_unique_record_ids(filename, validated)
        return tuple(validated)

    def _validate_record_identity(self, filename: str, record: BaseModel) -> None:
        values = record.model_dump(mode="python")
        schema_version = values.get("schema_version")
        data_version = values.get("data_version")
        if schema_version != self.manifest.schema_version:
            raise DataReleaseError(
                f"{filename} contains schema {schema_version}; "
                f"manifest requires {self.manifest.schema_version}"
            )
        if data_version != self.manifest.data_version:
            raise DataReleaseError(
                f"{filename} contains data version {data_version}; "
                f"manifest requires {self.manifest.data_version}"
            )

    @staticmethod
    def _validate_unique_record_ids(
        filename: str, records: tuple[RecordModel, ...] | list[RecordModel]
    ) -> None:
        identifiers = [
            record.source_id
            if isinstance(record, SourceRecord)
            else record.model_dump(mode="python")["record_id"]
            for record in records
        ]
        if len(identifiers) != len(set(identifiers)):
            raise DataReleaseError(f"Dataset {filename} contains duplicate primary keys")

    def _verify_declared_hash(self, filename: str, path: Path) -> None:
        entry = self.manifest.files.get(filename)
        if entry is None:
            raise DataReleaseError(f"Dataset is not declared by manifest: {filename}")
        actual = hashlib.sha256(_canonical_release_bytes(path.read_bytes())).hexdigest()
        if actual.lower() != entry.sha256.lower():
            raise DataReleaseError(f"Hash mismatch for {filename}")

    def _validate_manifest_datasets(self) -> None:
        declared = set(self.manifest.files)
        known = set(DATASET_MODELS)
        actual_csv = {path.name for path in self.release_dir.glob("*.csv")}
        missing = sorted(known - declared)
        unsupported = sorted(declared - known)
        unlisted = sorted(actual_csv - declared)
        if missing:
            raise DataReleaseError(f"Manifest is missing datasets: {missing}")
        if unsupported:
            raise DataReleaseError(f"Manifest declares unsupported datasets: {unsupported}")
        if unlisted:
            raise DataReleaseError(f"Release contains unlisted datasets: {unlisted}")
        for filename, entry in self.manifest.files.items():
            if entry.filename != filename:
                raise DataReleaseError(
                    f"Manifest entry filename mismatch: key {filename!r}, "
                    f"value {entry.filename!r}"
                )
            if entry.schema_version != self.manifest.schema_version:
                raise DataReleaseError(
                    f"Manifest entry {filename} has unsupported schema {entry.schema_version}"
                )

    @staticmethod
    def _source_ids(record: BaseModel) -> tuple[str, ...]:
        if isinstance(record, SourceRecord):
            return ()
        source_id = record.model_dump(mode="python").get("source_id", "")
        return tuple(part for part in source_id.split("|") if part)

    def _validate_cross_references(
        self,
        records: Mapping[str, tuple[BaseModel, ...]],
    ) -> None:
        sources = records["sources.csv"]
        source_ids = {record.source_id for record in sources if isinstance(record, SourceRecord)}
        if len(sources) != self.manifest.source_inventory_count:
            raise DataReleaseError(
                f"source inventory has {len(sources)} rows; "
                f"manifest declares {self.manifest.source_inventory_count}"
            )
        for filename, dataset in records.items():
            if filename == "sources.csv":
                continue
            for record in dataset:
                unknown = set(self._source_ids(record)) - source_ids
                if unknown:
                    raise DataReleaseError(
                        f"{filename} record {getattr(record, 'record_id', '<unknown>')} "
                        "references unknown sources: "
                        f"{sorted(unknown)}"
                    )

        unit_rates = cast(tuple[UnitRateRecord, ...], records["unit_rates.csv"])
        rate_ids = {rate.record_id for rate in unit_rates}
        rate_item_codes = {rate.item_code for rate in unit_rates}
        for template in records["boq_templates.csv"]:
            if isinstance(template, BOQTemplateRecord) and template.rate_id:
                if template.rate_id not in rate_ids | rate_item_codes:
                    raise DataReleaseError(
                        "BOQ template "
                        f"{getattr(template, 'record_id', '<unknown>')} references "
                        f"unknown rate {template.rate_id}"
                    )

        transformer_ratings = {
            transformer.rating_kva
            for transformer in records["transformers.csv"]
            if isinstance(transformer, TransformerRecord)
        }
        for price in records["transformer_prices.csv"]:
            if (
                isinstance(price, TransformerPriceRecord)
                and price.rating_kva not in transformer_ratings
            ):
                raise DataReleaseError(
                    f"Transformer price {price.record_id} has no matching transformer rating"
                )

    def load_snapshot(self) -> ReferenceSnapshot:
        """Load every declared dataset and return one immutable typed snapshot."""

        self._validate_manifest_datasets()
        records: dict[str, tuple[BaseModel, ...]] = {
            filename: self.load_dataset(filename, model)
            for filename, model in DATASET_MODELS.items()
        }
        self._validate_cross_references(records)
        sources = cast(tuple[SourceRecord, ...], records["sources.csv"])
        inverters = cast(tuple[InverterRecord, ...], records["inverters.csv"])
        cables = cast(tuple[CableRecord, ...], records["cables.csv"])
        ampacity = cast(tuple[AmpacityRecord, ...], records["ampacity.csv"])
        grouping_factors = cast(
            tuple[GroupingFactorRecord, ...], records["grouping_factors.csv"]
        )
        breakers = cast(tuple[BreakerRecord, ...], records["breakers.csv"])
        conduits = cast(tuple[ConduitRecord, ...], records["conduits.csv"])
        pe_mapping = cast(tuple[PEMappingRecord, ...], records["pe_mapping.csv"])
        transformers = cast(tuple[TransformerRecord, ...], records["transformers.csv"])
        transformer_prices = cast(
            tuple[TransformerPriceRecord, ...], records["transformer_prices.csv"]
        )
        unit_rates = cast(tuple[UnitRateRecord, ...], records["unit_rates.csv"])
        design_rules = cast(tuple[DesignRuleRecord, ...], records["design_rules.csv"])
        boq_templates = cast(tuple[BOQTemplateRecord, ...], records["boq_templates.csv"])
        return ReferenceSnapshot(
            schema_version=self.manifest.schema_version,
            data_version=self.manifest.data_version,
            release_status=self.manifest.release_status,
            release_date=self.manifest.release_date,
            manifest=self.manifest,
            files=tuple(self.manifest.files[filename] for filename in sorted(self.manifest.files)),
            sources=sources,
            inverters=inverters,
            cables=cables,
            ampacity=ampacity,
            grouping_factors=grouping_factors,
            breakers=breakers,
            conduits=conduits,
            pe_mapping=pe_mapping,
            transformers=transformers,
            transformer_prices=transformer_prices,
            unit_rates=unit_rates,
            design_rules=design_rules,
            boq_templates=boq_templates,
        )

    def snapshot(self) -> ReferenceSnapshot:
        """Backward-compatible alias for the typed snapshot API."""

        return self.load_snapshot()
