"""Pure adapters and lookups for ampacity correction-factor data."""

from __future__ import annotations

from collections.abc import Sequence

from solar_design.domain import EngineeringValidationError
from solar_design.models import (
    CorrectionFactor,
    GroupingFactorRecord,
    GroupingFactorSpec,
    RecordMetadata,
    ReferenceSnapshot,
)


def grouping_factor_from_record(record: GroupingFactorRecord) -> GroupingFactorSpec:
    """Convert one validated grouping row without changing its range or status."""

    return GroupingFactorSpec(
        metadata=RecordMetadata(
            record_id=record.record_id,
            revision=str(record.revision),
            verification_status=record.verification_status,
            source_id=record.source_id,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            notes=record.notes,
        ),
        installation_family=record.installation_family,
        min_groups=record.min_groups,
        max_groups=record.max_groups,
        factor=record.factor,
        counting_basis=record.counting_basis,
        conditions=record.conditions,
    )


def grouping_factors_from_records(
    records: Sequence[GroupingFactorRecord],
) -> tuple[GroupingFactorSpec, ...]:
    """Adapt grouping rows from a validated release into immutable engine records."""

    return tuple(grouping_factor_from_record(record) for record in records)


def grouping_factors_from_snapshot(
    snapshot: ReferenceSnapshot,
) -> tuple[GroupingFactorSpec, ...]:
    """Build grouping-factor records from one pinned reference snapshot."""

    return grouping_factors_from_records(snapshot.grouping_factors)


def select_grouping_factor(
    group_count: int,
    factors: Sequence[GroupingFactorSpec],
    *,
    installation_family: str = "SAME_RACEWAY",
) -> CorrectionFactor:
    """Select exactly one factor whose inclusive range contains ``group_count``."""

    if group_count <= 0:
        raise EngineeringValidationError("group_count", "must be greater than zero", group_count)
    matches = [
        item
        for item in factors
        if item.installation_family == installation_family
        and item.min_groups <= group_count <= item.max_groups
    ]
    if len(matches) != 1:
        if not matches:
            raise EngineeringValidationError(
                "group_count",
                "has no applicable grouping factor for the installation family",
                group_count,
            )
        raise EngineeringValidationError(
            "grouping_factors",
            "has overlapping applicable ranges",
            tuple(item.record_id for item in matches),
        )
    return matches[0].as_correction_factor()
