"""Pure adapters for incomplete and draft breaker reference records."""

from __future__ import annotations

from collections.abc import Sequence

from solar_design.models import (
    BreakerRecord,
    ProtectionCandidate,
    RecordMetadata,
    ReferenceSnapshot,
)


def protection_candidate_from_record(record: BreakerRecord) -> ProtectionCandidate:
    """Convert a validated breaker row while preserving missing fields as ``None``."""

    return ProtectionCandidate(
        metadata=RecordMetadata(
            record_id=record.record_id,
            revision=str(record.revision),
            verification_status=record.verification_status,
            source_id=record.source_id,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            notes=record.notes,
        ),
        role=record.role,
        manufacturer=record.manufacturer,
        model=record.model,
        poles=record.poles,
        voltage_v=record.voltage_v,
        trip_setting_a=record.trip_setting_a,
        frame_rating_a=record.frame_rating_a,
        breaking_capacity_ka=record.breaking_capacity_ka,
        terminal_temperature_c=record.terminal_temp_c,
        adjustable_settings=record.adjustable_settings,
        coordination_status=record.coordination_status,
    )


def protection_candidates_from_records(
    records: Sequence[BreakerRecord],
) -> tuple[ProtectionCandidate, ...]:
    """Adapt breaker rows from a validated release into immutable candidates."""

    return tuple(protection_candidate_from_record(record) for record in records)


def protection_candidates_from_snapshot(
    snapshot: ReferenceSnapshot,
) -> tuple[ProtectionCandidate, ...]:
    """Build protection candidates from one pinned reference snapshot."""

    return protection_candidates_from_records(snapshot.breakers)
