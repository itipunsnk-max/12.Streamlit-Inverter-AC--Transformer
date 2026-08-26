"""Internal deterministic helpers shared by calculation modules."""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal
from hashlib import sha256

from solar_design.domain import Finding, FindingSeverity, VerificationStatus

SQRT_THREE = Decimal(3).sqrt()
HUNDRED = Decimal("100")


def ceil_decimal(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def stable_decision_id(rule_id: str, *parts: object) -> str:
    material = "|".join((rule_id, *(str(part) for part in parts)))
    return f"{rule_id}:{sha256(material.encode('utf-8')).hexdigest()[:16]}"


def rule_status_finding(
    rule_id: str,
    status: VerificationStatus,
    source_ids: tuple[str, ...],
) -> tuple[Finding, ...]:
    if status is VerificationStatus.VERIFIED:
        return ()
    if status is VerificationStatus.NOT_PERMITTED:
        severity = FindingSeverity.BLOCKER
    elif status in (VerificationStatus.UNKNOWN, VerificationStatus.REQUIRES_UTILITY_APPROVAL):
        severity = FindingSeverity.WARNING
    else:
        severity = FindingSeverity.REVIEW
    return (
        Finding(
            code="RULE_NOT_VERIFIED",
            message=f"Rule {rule_id} has status {status.value}; engineering review is required.",
            severity=severity,
            verification_status=status,
            source_ids=source_ids,
        ),
    )
