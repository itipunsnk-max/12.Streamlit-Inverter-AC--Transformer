"""Apply explicit user BOQ deltas without mutating the generated baseline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields, replace
from decimal import Decimal
from enum import Enum
from typing import Any

from .models import BOQBaseline, BOQDelta, BOQDeltaOperation, BOQLine, BOQRevision
from .validation import find_duplicate_scopes

_UPDATABLE_FIELDS = {item.name for item in fields(BOQLine)} - {"line_id", "template_item_id"}


def apply_boq_deltas(
    baseline: BOQBaseline,
    deltas: tuple[BOQDelta, ...] = (),
) -> BOQRevision:
    """Return a revision produced from a baseline and an ordered, unique delta set."""

    by_id = {line.line_id: line for line in baseline.lines}
    unique_deltas: dict[str, BOQDelta] = {}
    for delta in deltas:
        previous = unique_deltas.get(delta.delta_id)
        if previous is not None and previous != delta:
            raise ValueError(f"conflicting payloads for delta_id {delta.delta_id!r}")
        unique_deltas[delta.delta_id] = delta

    ordered = tuple(sorted(unique_deltas.values(), key=lambda item: (item.sequence, item.delta_id)))
    for delta in ordered:
        if delta.operation is BOQDeltaOperation.ADD:
            if delta.target_line_id in by_id:
                if by_id[delta.target_line_id] == delta.added_line:
                    continue
                raise ValueError(f"cannot add existing BOQ line {delta.target_line_id!r}")
            assert delta.added_line is not None
            by_id[delta.target_line_id] = delta.added_line
        elif delta.operation is BOQDeltaOperation.REMOVE:
            by_id.pop(delta.target_line_id, None)
        else:
            current = by_id.get(delta.target_line_id)
            if current is None:
                raise ValueError(f"cannot update missing BOQ line {delta.target_line_id!r}")
            unknown = set(delta.changes) - _UPDATABLE_FIELDS
            if unknown:
                raise ValueError(f"unsupported BOQ fields in delta: {sorted(unknown)}")
            by_id[delta.target_line_id] = replace(current, **dict(delta.changes))

    lines = tuple(sorted(by_id.values(), key=lambda item: (item.sort_order, item.line_id)))
    revision_id = _content_id(
        {
            "baseline_id": baseline.baseline_id,
            "deltas": ordered,
            "lines": lines,
        },
        prefix="boqrev",
    )
    return BOQRevision(
        revision_id=revision_id,
        baseline_id=baseline.baseline_id,
        design_run_id=baseline.design_run_id,
        lines=lines,
        deltas=ordered,
        findings=find_duplicate_scopes(lines),
    )


def content_id(value: object, *, prefix: str) -> str:
    return _content_id(value, prefix=prefix)


def _content_id(value: object, *, prefix: str) -> str:
    payload = json.dumps(
        _canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _canonical(value: object) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {item.name: _canonical(getattr(value, item.name)) for item in fields(value)}  # type: ignore[arg-type]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(_canonical(item) for item in value)
    return value
