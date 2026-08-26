"""Phase 1 contract tests for models, release loading, and migrations."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from solar_design.models import (
    DATASET_MODELS,
    AmpacityDataRecord,
    BOQTemplateRecord,
    BreakerRecord,
    CableDataRecord,
    ConduitDataRecord,
    DesignRuleRecord,
    GroupingFactorRecord,
    InverterRecord,
    MigrationRegistry,
    MigrationStep,
    PEMappingRecord,
    Quantity,
    ReferenceSnapshot,
    ReleaseManifest,
    SchemaMigrationError,
    SchemaVersion,
    SourceRecord,
    TransformerPriceRecord,
    TransformerRecord,
    Unit,
    UnitRateRecord,
    migrate_payload,
)
from solar_design.repositories import DataReleaseError, ReleaseRepository
from solar_design.repositories.release import _canonical_release_bytes

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "data" / "releases" / "2026.08-draft"


def test_current_release_loads_all_declared_datasets_into_an_immutable_snapshot() -> None:
    repository = ReleaseRepository(RELEASE)
    snapshot = repository.load_snapshot()

    assert repository.data_version == "2026.08-draft"
    assert set(repository.manifest.files) == set(DATASET_MODELS)
    assert len(snapshot.sources) == repository.manifest.source_inventory_count
    assert len(snapshot.inverters) == 6
    assert len(snapshot.design_rules) == 6
    assert len(snapshot.boq_templates) == 2
    assert snapshot.source_hashes

    with pytest.raises(ValidationError):
        snapshot.data_version = "changed"


def test_release_hash_validation_is_stable_across_windows_crlf_checkout() -> None:
    lf_payload = b"record_id,value\nROW-1,Thai text\n"
    crlf_payload = lf_payload.replace(b"\n", b"\r\n")

    assert _canonical_release_bytes(crlf_payload) == lf_payload


def test_manifest_and_unit_models_round_trip_through_json() -> None:
    repository = ReleaseRepository(RELEASE)
    restored = ReleaseManifest.model_validate_json(repository.manifest.model_dump_json())
    assert restored == repository.manifest
    assert Quantity(value=Decimal("400"), unit=Unit.VOLT).value == 400


def test_each_declared_dataset_validates_against_its_pydantic_contract() -> None:
    repository = ReleaseRepository(RELEASE)

    for filename, model in DATASET_MODELS.items():
        records = repository.load_dataset(filename, model)
        assert records


def test_pydantic_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        InverterRecord.model_validate(
            {
                "record_id": "INV-TEST",
                "schema_version": "1.0.0",
                "data_version": "test",
                "revision": 1,
                "manufacturer": "Test",
                "model": "Test",
                "ac_power_kw": "10",
                "verification_status": "DRAFT",
                "source_id": "SRC-TEST-001",
                "unknown_dangerous_field": "must be rejected",
            }
        )


def test_release_rejects_undeclared_or_unsafe_dataset_paths() -> None:
    repository = ReleaseRepository(RELEASE)

    with pytest.raises(DataReleaseError):
        repository.load_csv("../sources.csv")
    with pytest.raises(DataReleaseError):
        repository.load_csv("not-declared.csv")


def test_migration_contract_is_explicit_and_does_not_mutate_input() -> None:
    payload = {"schema_version": "1.0.0", "value": "unchanged"}
    migrated = migrate_payload(payload)
    assert migrated == payload
    assert payload["schema_version"] == "1.0.0"

    registry = MigrationRegistry(
        (
            MigrationStep(
                SchemaVersion(1, 0, 0),
                SchemaVersion(1, 1, 0),
                lambda item: {**item, "added": True},
            ),
        )
    )
    migrated = registry.migrate(payload, target_version="1.1.0")
    assert migrated == {"schema_version": "1.1.0", "value": "unchanged", "added": True}
    assert "added" not in payload

    with pytest.raises(SchemaMigrationError):
        migrate_payload({"schema_version": "2.0.0"})


def test_reference_snapshot_rejects_an_unknown_source_reference() -> None:
    repository = ReleaseRepository(RELEASE)
    records = {
        filename: repository.load_dataset(filename, model)
        for filename, model in DATASET_MODELS.items()
    }
    sources = cast(tuple[SourceRecord, ...], records["sources.csv"])
    inverters = cast(tuple[InverterRecord, ...], records["inverters.csv"])
    cables = cast(tuple[CableDataRecord, ...], records["cables.csv"])
    ampacity = cast(tuple[AmpacityDataRecord, ...], records["ampacity.csv"])
    grouping_factors = cast(tuple[GroupingFactorRecord, ...], records["grouping_factors.csv"])
    breakers = cast(tuple[BreakerRecord, ...], records["breakers.csv"])
    conduits = cast(tuple[ConduitDataRecord, ...], records["conduits.csv"])
    pe_mapping = cast(tuple[PEMappingRecord, ...], records["pe_mapping.csv"])
    transformers = cast(tuple[TransformerRecord, ...], records["transformers.csv"])
    transformer_prices = cast(
        tuple[TransformerPriceRecord, ...], records["transformer_prices.csv"]
    )
    unit_rates = cast(tuple[UnitRateRecord, ...], records["unit_rates.csv"])
    design_rules = cast(tuple[DesignRuleRecord, ...], records["design_rules.csv"])
    boq_templates = cast(tuple[BOQTemplateRecord, ...], records["boq_templates.csv"])
    first = inverters[0]
    inverters = (
        first.model_copy(update={"source_id": "SRC-NOT-IN-REGISTRY"}),
        *inverters[1:],
    )

    with pytest.raises(ValidationError):
        ReferenceSnapshot(
            schema_version=repository.manifest.schema_version,
            data_version=repository.manifest.data_version,
            release_status=repository.manifest.release_status,
            release_date=repository.manifest.release_date,
            manifest=repository.manifest,
            files=tuple(repository.manifest.files.values()),
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
