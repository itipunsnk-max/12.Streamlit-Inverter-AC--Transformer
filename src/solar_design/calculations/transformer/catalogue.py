"""Adapters for incomplete transformer reference rows and standard ratings."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from solar_design.models import (
    RecordMetadata,
    ReferenceSnapshot,
    TransformerRecord,
    TransformerSpec,
)


def transformer_spec_from_record(record: TransformerRecord) -> TransformerSpec:
    """Adapt a transformer row without inventing missing electrical data."""

    return TransformerSpec(
        metadata=RecordMetadata(
            record_id=record.record_id,
            revision=str(record.revision),
            verification_status=record.verification_status,
            source_id=record.source_id,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            notes=record.notes,
        ),
        manufacturer=record.manufacturer,
        model=record.model,
        rating_kva=record.rating_kva,
        high_voltage_v=record.hv_voltage_v,
        low_voltage_v=record.lv_voltage_v,
        phases=record.phases,
        vector_group=record.vector_group,
        impedance_percent=record.impedance_pct,
        # The release has no approved utility installation eligibility table.
        allowed_installation_types=(),
    )


def transformer_specs_from_records(
    records: Sequence[TransformerRecord],
) -> tuple[TransformerSpec, ...]:
    """Adapt transformer rows while preserving nullable product fields."""

    return tuple(transformer_spec_from_record(record) for record in records)


def transformer_specs_from_snapshot(
    snapshot: ReferenceSnapshot,
) -> tuple[TransformerSpec, ...]:
    """Build transformer entries from one immutable reference snapshot."""

    return transformer_specs_from_records(snapshot.transformers)


def standard_transformer_ratings_from_records(
    records: Sequence[TransformerRecord],
) -> tuple[Decimal, ...]:
    """Return the exact supplied standard rating set, with no interpolation."""

    return tuple(sorted({record.rating_kva for record in records}))


def standard_transformer_ratings_from_snapshot(
    snapshot: ReferenceSnapshot,
) -> tuple[Decimal, ...]:
    """Read standard ratings from the pinned release rather than a guessed list."""

    return standard_transformer_ratings_from_records(snapshot.transformers)
