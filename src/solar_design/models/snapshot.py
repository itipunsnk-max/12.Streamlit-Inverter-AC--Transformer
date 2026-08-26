"""Immutable, typed reference snapshot consumed by future design runs."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from .manifest import DatasetManifestEntry, ReleaseManifest, ReleaseStatus
from .schemas import (
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


class ReferenceSnapshot(BaseModel):
    """All data used by a calculation, pinned to one release manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    data_version: str
    release_status: ReleaseStatus
    release_date: date
    manifest: ReleaseManifest
    files: tuple[DatasetManifestEntry, ...]
    sources: tuple[SourceRecord, ...]
    inverters: tuple[InverterRecord, ...]
    cables: tuple[CableRecord, ...]
    ampacity: tuple[AmpacityRecord, ...]
    grouping_factors: tuple[GroupingFactorRecord, ...]
    breakers: tuple[BreakerRecord, ...]
    conduits: tuple[ConduitRecord, ...]
    pe_mapping: tuple[PEMappingRecord, ...]
    transformers: tuple[TransformerRecord, ...]
    transformer_prices: tuple[TransformerPriceRecord, ...]
    unit_rates: tuple[UnitRateRecord, ...]
    design_rules: tuple[DesignRuleRecord, ...]
    boq_templates: tuple[BOQTemplateRecord, ...]

    @model_validator(mode="after")
    def validate_identity(self) -> ReferenceSnapshot:
        if self.manifest.data_version != self.data_version:
            raise ValueError("snapshot data_version does not match its manifest")
        if self.manifest.schema_version != self.schema_version:
            raise ValueError("snapshot schema_version does not match its manifest")
        source_ids = {source.source_id for source in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("source IDs must be unique")
        for collection in (
            self.inverters,
            self.cables,
            self.ampacity,
            self.grouping_factors,
            self.breakers,
            self.conduits,
            self.pe_mapping,
            self.transformers,
            self.transformer_prices,
            self.unit_rates,
            self.design_rules,
            self.boq_templates,
        ):
            record_ids = [record.record_id for record in collection]
            if len(record_ids) != len(set(record_ids)):
                raise ValueError("record IDs must be unique within each dataset")
            for record in collection:
                if not set(record.source_ids) <= source_ids:
                    raise ValueError(f"record {record.record_id} references an unknown source")
        return self

    @property
    def source_hashes(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted((filename, entry.sha256) for filename, entry in self.manifest.files.items())
        )
