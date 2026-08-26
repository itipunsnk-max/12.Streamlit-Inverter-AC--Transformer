"""Phase 1 contract tests for models, release loading, and migrations."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from solar_design.models import (
    DATASET_MODELS,
    InverterRecord,
    MigrationRegistry,
    MigrationStep,
    Quantity,
    ReferenceSnapshot,
    ReleaseManifest,
    SchemaMigrationError,
    SchemaVersion,
    Unit,
    migrate_payload,
)
from solar_design.repositories import DataReleaseError, ReleaseRepository

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
        snapshot.data_version = "changed"  # type: ignore[misc]


def test_manifest_and_unit_models_round_trip_through_json() -> None:
    repository = ReleaseRepository(RELEASE)
    restored = ReleaseManifest.model_validate_json(repository.manifest.model_dump_json())
    assert restored == repository.manifest
    assert Quantity(value="400", unit=Unit.VOLT).value == 400


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
    first = records["inverters.csv"][0]
    records["inverters.csv"] = (
        first.model_copy(update={"source_id": "SRC-NOT-IN-REGISTRY"}),
        *records["inverters.csv"][1:],
    )

    with pytest.raises(ValidationError):
        ReferenceSnapshot(
            schema_version=repository.manifest.schema_version,
            data_version=repository.manifest.data_version,
            release_status=repository.manifest.release_status,
            release_date=repository.manifest.release_date,
            manifest=repository.manifest,
            files=tuple(repository.manifest.files.values()),
            sources=records["sources.csv"],
            inverters=records["inverters.csv"],
            cables=records["cables.csv"],
            ampacity=records["ampacity.csv"],
            grouping_factors=records["grouping_factors.csv"],
            breakers=records["breakers.csv"],
            conduits=records["conduits.csv"],
            pe_mapping=records["pe_mapping.csv"],
            transformers=records["transformers.csv"],
            transformer_prices=records["transformer_prices.csv"],
            unit_rates=records["unit_rates.csv"],
            design_rules=records["design_rules.csv"],
            boq_templates=records["boq_templates.csv"],
        )
