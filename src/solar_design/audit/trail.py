"""Deterministic, append-only audit events.

Timestamps and actor identities are supplied by the application layer.  This keeps
the model deterministic and prevents pure calculation functions from reading the
clock or session state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AuditAction(StrEnum):
    INPUT_VALIDATED = "INPUT_VALIDATED"
    DESIGN_CALCULATED = "DESIGN_CALCULATED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"
    BOQ_GENERATED = "BOQ_GENERATED"
    BOQ_EDITED = "BOQ_EDITED"
    COST_CALCULATED = "COST_CALCULATED"
    RATE_CHANGED = "RATE_CHANGED"
    EXPORT_PRODUCED = "EXPORT_PRODUCED"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    sequence: int
    occurred_at: str
    actor: str
    action: AuditAction
    aggregate_type: str
    aggregate_id: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must not be blank")
        if self.sequence < 1:
            raise ValueError("sequence must be at least 1")
        if not self.occurred_at.strip():
            raise ValueError("occurred_at must be an ISO-8601 string")
        if not self.actor.strip():
            raise ValueError("actor must not be blank")
        if not self.aggregate_type.strip() or not self.aggregate_id.strip():
            raise ValueError("aggregate type and id must not be blank")


@dataclass(frozen=True, slots=True)
class AuditTrail:
    """An immutable event sequence with strict ordering and duplicate protection."""

    events: tuple[AuditEvent, ...] = ()

    def __post_init__(self) -> None:
        ids = [event.event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("audit event ids must be unique")
        expected = list(range(1, len(self.events) + 1))
        actual = [event.sequence for event in self.events]
        if actual != expected:
            raise ValueError("audit event sequence must be contiguous and start at 1")

    def append(
        self,
        *,
        event_id: str,
        occurred_at: str,
        actor: str,
        action: AuditAction,
        aggregate_type: str,
        aggregate_id: str,
        details: Mapping[str, Any] | None = None,
    ) -> AuditTrail:
        event = AuditEvent(
            event_id=event_id,
            sequence=len(self.events) + 1,
            occurred_at=occurred_at,
            actor=actor,
            action=action,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            details={} if details is None else dict(details),
        )
        return AuditTrail(events=(*self.events, event))
