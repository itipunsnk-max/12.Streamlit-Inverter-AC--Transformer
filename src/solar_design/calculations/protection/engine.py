"""Explicit placeholder until fault level and coordination rules are approved."""

from __future__ import annotations

from collections.abc import Sequence

from solar_design.calculations._support import stable_decision_id
from solar_design.domain import (
    AssessmentStatus,
    CandidateRecord,
    DecisionRecord,
    Finding,
    FindingSeverity,
    TraceValue,
    VerificationStatus,
)
from solar_design.models import BreakerSpec, ProtectionCandidate, ProtectionSelection
from solar_design.rules import RULES
from solar_design.validation import DecimalLike, EngineeringValidationError, require_positive

ProtectionCatalogueItem = BreakerSpec | ProtectionCandidate


def select_protection(
    load_current_a: DecimalLike,
    catalogue: Sequence[ProtectionCatalogueItem] = (),
) -> ProtectionSelection:
    """Return NOT_ASSESSED without presenting a breaker recommendation.

    Catalogue candidates are recorded for traceability only. Selecting solely
    by current would omit fault duty, coordination, terminal and utility rules.
    """

    load = require_positive(load_current_a, "load_current_a")
    candidate_ids = [item.record_id for item in catalogue]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise EngineeringValidationError("catalogue", "contains duplicate breaker record IDs")

    source_ids: list[str] = []
    candidate_findings: list[Finding] = []
    candidate_records: list[CandidateRecord] = []
    for item in catalogue:
        item_source_ids = item.metadata.source_ids
        for source_id in item_source_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
        reasons = [
            "catalogue item retained for review only",
            "fault level and coordination are not available",
        ]
        if item.metadata.verification_status is not VerificationStatus.VERIFIED:
            reasons.append(
                f"catalogue verification status is {item.metadata.verification_status.value}"
            )
            candidate_findings.append(
                Finding(
                    "PROTECTION_CANDIDATE_NOT_VERIFIED",
                    f"Breaker candidate {item.record_id} is not verified and cannot be "
                    "recommended.",
                    FindingSeverity.WARNING,
                    item.metadata.verification_status,
                    item_source_ids,
                )
            )
        candidate_records.append(CandidateRecord(item.record_id, False, tuple(reasons)))

    finding = Finding(
        "PROTECTION_NOT_ASSESSED",
        "Breaker sizing, interrupting capacity and protection coordination "
        "require approved project rules and fault data.",
        FindingSeverity.WARNING,
        VerificationStatus.UNKNOWN,
        tuple(source_ids),
    )
    findings = (finding, *candidate_findings)
    rule = RULES.get("PROTECTION-PLACEHOLDER")
    decision = DecisionRecord(
        stable_decision_id("PROTECTION-PLACEHOLDER", load),
        "protection",
        rule.rule_id,
        rule.version,
        rule.verification_status,
        (
            TraceValue("load_current", load, "A"),
            TraceValue("catalogue_candidate_count", len(catalogue)),
        ),
        selected_values=(TraceValue("assessment_status", AssessmentStatus.NOT_ASSESSED.value),),
        candidates=tuple(candidate_records),
        source_ids=tuple(source_ids),
        findings=findings,
    )
    return ProtectionSelection(
        AssessmentStatus.NOT_ASSESSED,
        load,
        None,
        findings,
        decision,
    )
