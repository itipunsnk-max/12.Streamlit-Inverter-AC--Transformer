"""Immutable and serialization-friendly engineering trace records."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .enums import FindingSeverity, VerificationStatus
from .exceptions import EngineeringValidationError

Scalar = Decimal | str | int | bool | None


@dataclass(frozen=True, slots=True)
class TraceValue:
    name: str
    value: Scalar
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    message: str
    severity: FindingSeverity
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    source_ids: tuple[str, ...] = ()
    field: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    candidate_id: str
    accepted: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Complete evidence for one calculation or selection decision."""

    decision_id: str
    engine: str
    rule_id: str
    rule_version: str
    verification_status: VerificationStatus
    inputs: tuple[TraceValue, ...]
    calculated_values: tuple[TraceValue, ...] = ()
    selected_values: tuple[TraceValue, ...] = ()
    intermediate_values: tuple[TraceValue, ...] = ()
    candidates: tuple[CandidateRecord, ...] = ()
    source_ids: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()
    override_reason: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.verification_status is VerificationStatus.USER_OVERRIDE:
            if not self.override_reason or not self.override_reason.strip():
                raise EngineeringValidationError(
                    "override_reason",
                    "a non-blank reason is required for USER_OVERRIDE",
                    self.override_reason,
                )

    @property
    def has_blocker(self) -> bool:
        return any(item.severity is FindingSeverity.BLOCKER for item in self.findings)
