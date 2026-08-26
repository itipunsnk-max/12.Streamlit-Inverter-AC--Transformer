"""Adapters from the pinned reference release to the Phase 4 wiring engines."""

from __future__ import annotations

from collections.abc import Sequence

from solar_design.models import (
    AmpacityDataRecord,
    AmpacityRecord,
    CableDataRecord,
    CableSpec,
    ConduitDataRecord,
    ConduitSpec,
    PEMappingRecord,
    PESelectionRule,
    RecordMetadata,
    ReferenceRecord,
    ReferenceSnapshot,
)


def _metadata(record: ReferenceRecord) -> RecordMetadata:
    """Build calculation metadata without changing release values."""

    return RecordMetadata(
        record_id=record.record_id,
        revision=str(record.revision),
        verification_status=record.verification_status,
        source_id=record.source_id,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        notes=record.notes,
    )


def cable_spec_from_record(record: CableDataRecord) -> CableSpec:
    """Adapt a cable row and preserve incomplete manufacturer fields as ``None``."""

    return CableSpec(
        metadata=_metadata(record),
        manufacturer=record.manufacturer,
        model=record.model,
        family=record.family,
        material=record.conductor_material,
        insulation=record.insulation,
        voltage_class_v=record.voltage_class_v,
        cores=record.cores,
        cross_section_mm2=record.csa_mm2,
        outside_diameter_mm=record.outside_diameter_mm,
        temperature_rating_c=record.conductor_temp_c,
        system=record.system,
    )


def cable_specs_from_records(records: Sequence[CableDataRecord]) -> tuple[CableSpec, ...]:
    """Adapt validated cable rows without filling OD, material, or temperature gaps."""

    return tuple(cable_spec_from_record(record) for record in records)


def cable_specs_from_snapshot(snapshot: ReferenceSnapshot) -> tuple[CableSpec, ...]:
    """Build cable catalogue entries from one immutable reference snapshot."""

    return cable_specs_from_records(snapshot.cables)


def pe_selection_rule_from_record(record: PEMappingRecord) -> PESelectionRule:
    """Adapt one PE row for exact lookup only."""

    return PESelectionRule(
        metadata=_metadata(record),
        phase_cross_section_mm2=record.phase_csa_mm2,
        pe_cross_section_mm2=record.pe_csa_mm2,
        phase_material=record.phase_material,
        pe_material=record.pe_material,
    )


def pe_selection_rules_from_records(
    records: Sequence[PEMappingRecord],
) -> tuple[PESelectionRule, ...]:
    """Adapt PE mappings without interpolation or arithmetic substitution."""

    return tuple(pe_selection_rule_from_record(record) for record in records)


def pe_selection_rules_from_snapshot(
    snapshot: ReferenceSnapshot,
) -> tuple[PESelectionRule, ...]:
    """Build exact PE lookup entries from one immutable reference snapshot."""

    return pe_selection_rules_from_records(snapshot.pe_mapping)


def conduit_spec_from_record(record: ConduitDataRecord) -> ConduitSpec:
    """Use certified ID when available; otherwise retain screening-only status."""

    certified = record.certified_internal_diameter_mm
    return ConduitSpec(
        metadata=_metadata(record),
        conduit_type=record.series,
        trade_size=record.trade_size_in,
        internal_diameter_mm=certified or record.screening_internal_diameter_mm,
        standard=record.standard_listing,
        is_screening_dimension=certified is None,
    )


def conduit_specs_from_records(
    records: Sequence[ConduitDataRecord],
) -> tuple[ConduitSpec, ...]:
    """Adapt conduit rows while marking non-certified IDs as screening dimensions."""

    return tuple(conduit_spec_from_record(record) for record in records)


def conduit_specs_from_snapshot(snapshot: ReferenceSnapshot) -> tuple[ConduitSpec, ...]:
    """Build conduit catalogue entries from one immutable reference snapshot."""

    return conduit_specs_from_records(snapshot.conduits)


def ampacity_record_for_cable(
    record: AmpacityDataRecord,
    cable: CableSpec,
) -> AmpacityRecord | None:
    """Link an ampacity row to a cable only on explicit physical identity fields."""

    if record.csa_mm2 != cable.cross_section_mm2 or record.cores != cable.cores:
        return None
    if cable.material is not None and (
        cable.material.casefold() != record.conductor_material.casefold()
    ):
        return None
    if cable.insulation is not None and (
        cable.insulation.casefold() != record.insulation.casefold()
    ):
        return None
    if (
        cable.temperature_rating_c is not None
        and cable.temperature_rating_c != record.conductor_temp_c
    ):
        return None
    return AmpacityRecord(
        metadata=_metadata(record),
        cable_id=cable.record_id,
        installation_method=record.installation_method,
        current_carrying_conductors=record.current_carrying_conductors,
        reference_ambient_c=record.reference_ambient_c,
        ampacity_a=record.ampacity_a,
    )


def ampacity_records_for_cables(
    records: Sequence[AmpacityDataRecord],
    cables: Sequence[CableSpec],
) -> tuple[AmpacityRecord, ...]:
    """Create linked engine rows only where CSA/core/material identity is compatible."""

    linked: list[AmpacityRecord] = []
    for record in records:
        linked.extend(
            linked_record
            for cable in cables
            if (linked_record := ampacity_record_for_cable(record, cable)) is not None
        )
    return tuple(linked)


def ampacity_records_from_snapshot(
    snapshot: ReferenceSnapshot,
    cables: Sequence[CableSpec] | None = None,
) -> tuple[AmpacityRecord, ...]:
    """Link release ampacity rows to the snapshot cable catalogue."""

    catalogue = cable_specs_from_snapshot(snapshot) if cables is None else tuple(cables)
    return ampacity_records_for_cables(snapshot.ampacity, catalogue)
