"""Adapters from the validated BOQ template release to immutable BOQ models."""

from __future__ import annotations

from collections.abc import Sequence

from solar_design.models import BOQTemplateRecord, ReferenceSnapshot

from .models import BOQTemplate, BOQTemplateItem, CostStatus, PricingMode


def boq_template_item_from_record(record: BOQTemplateRecord) -> BOQTemplateItem:
    """Adapt one release row without executing arbitrary condition text."""

    if record.condition_key.strip().upper() != "ALWAYS":
        raise ValueError(
            f"unsupported BOQ condition key {record.condition_key!r}; "
            "register an explicit condition mapping before use"
        )
    parameters = {}
    if record.quantity_rule_key.strip().lower() == "fixed":
        if record.default_quantity is None:
            raise ValueError(f"fixed BOQ row {record.record_id!r} has no default quantity")
        parameters["quantity"] = record.default_quantity
    return BOQTemplateItem(
        item_id=record.record_id,
        category=record.category,
        description_th=record.description_th,
        description_en=record.description_en,
        unit=record.unit,
        pricing_mode=PricingMode(record.pricing_mode.strip().upper()),
        quantity_rule_key=record.quantity_rule_key,
        quantity_parameters=parameters,
        conditions={"installation_type": record.installation_type},
        cost_status=CostStatus(record.cost_status.strip().upper()),
        include_in_total=record.cost_status.strip().upper() != CostStatus.EXCL.value,
        sort_order=record.display_order,
        rate_id=record.rate_id,
        duplicate_scope_group=record.duplicate_scope_group,
        source_ids=tuple(part.strip() for part in record.source_id.split("|") if part.strip()),
        verification_status=record.verification_status,
        notes=(record.notes,) if record.notes else (),
    )


def boq_template_from_records(
    records: Sequence[BOQTemplateRecord],
    *,
    installation_type: str | None = None,
    template_id: str | None = None,
) -> BOQTemplate:
    """Build a deterministic template from one installation-type slice."""

    selected = tuple(
        record
        for record in records
        if installation_type is None
        or record.installation_type.casefold() == installation_type.casefold()
    )
    if not selected:
        raise ValueError("no BOQ template rows match the requested installation type")
    resolved_type = installation_type or selected[0].installation_type
    revisions = {str(record.revision) for record in selected}
    if len(revisions) != 1:
        raise ValueError("BOQ template rows have mixed revisions")
    return BOQTemplate(
        template_id=template_id or f"BOQ-{resolved_type.upper()}",
        revision=next(iter(revisions)),
        installation_type=resolved_type,
        items=tuple(
            boq_template_item_from_record(record)
            for record in sorted(selected, key=lambda item: (item.display_order, item.record_id))
        ),
    )


def boq_template_from_snapshot(
    snapshot: ReferenceSnapshot,
    *,
    installation_type: str | None = None,
    template_id: str | None = None,
) -> BOQTemplate:
    """Build a template from one pinned reference snapshot."""

    return boq_template_from_records(
        snapshot.boq_templates,
        installation_type=installation_type,
        template_id=template_id,
    )
