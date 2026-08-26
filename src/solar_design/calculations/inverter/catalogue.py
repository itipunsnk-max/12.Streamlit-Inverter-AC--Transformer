"""Pure adapters from the validated reference snapshot to inverter engines."""

from __future__ import annotations

from collections.abc import Sequence

from solar_design.models import InverterRecord, InverterSpec, RecordMetadata, ReferenceSnapshot


def inverter_spec_from_record(record: InverterRecord) -> InverterSpec:
    """Convert one validated inverter row without filling unknown engineering data."""

    return InverterSpec(
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
        ac_power_kw=record.ac_power_kw,
        ac_voltage_v=record.nominal_voltage_v,
        phases=record.phases,
        ac_apparent_power_kva=record.ac_apparent_power_kva,
        nominal_current_a=record.nominal_ac_current_a,
        maximum_output_current_a=record.max_ac_current_a,
        minimum_power_factor=record.pf_min,
        maximum_dc_power_kwp=record.recommended_max_dc_kwp,
        dc_ac_ratio=record.dc_ac_ratio,
        maximum_dc_input_current_a=record.max_dc_input_current_a,
        ambient_reference_c=record.ambient_reference_c,
        mppt_count=record.mppt_count,
        maximum_input_current_per_mppt_a=None,
    )


def inverter_specs_from_records(records: Sequence[InverterRecord]) -> tuple[InverterSpec, ...]:
    """Adapt a validated sequence while preserving missing limits as ``None``."""

    return tuple(inverter_spec_from_record(record) for record in records)


def inverter_specs_from_snapshot(snapshot: ReferenceSnapshot) -> tuple[InverterSpec, ...]:
    """Build the immutable engine catalogue from one pinned reference snapshot."""

    return inverter_specs_from_records(snapshot.inverters)
