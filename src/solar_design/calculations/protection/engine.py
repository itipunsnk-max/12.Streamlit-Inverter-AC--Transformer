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
from solar_design.models import BreakerSpec, ProtectionSelection
from solar_design.rules import RULES
from solar_design.validation import DecimalLike, require_positive


def select_protection(
    load_current_a: DecimalLike,
    catalogue: Sequence[BreakerSpec] = (),
) -> ProtectionSelection:
    """Return NOT_ASSESSED without presenting a breaker recommendation.

    Catalogue candidates are recorded for traceability only. Selecting solely
    by current would omit fault duty, coordination, terminal and utility rules.
    """

    load = require_positive(load_current_a, "load_current_a")
    finding = Finding(
        "PROTECTION_NOT_ASSESSED",
        "Breaker sizing, interrupting capacity and protection coordination "
        "require approved project rules and fault data.",
        FindingSeverity.WARNING,
        VerificationStatus.UNKNOWN,
    )
    candidates = tuple(
        CandidateRecord(
            item.record_id,
            False,
            (
                "catalogue item retained for review only",
                "fault level and coordination are not available",
            ),
        )
        for item in catalogue
    )
    rule = RULES.get("PROTECTION-PLACEHOLDER")
    decision = DecisionRecord(
        stable_decision_id("PROTECTION-PLACEHOLDER", load),
        "protection",
        rule.rule_id,
        rule.version,
        rule.verification_status,
        (TraceValue("load_current", load, "A"),),
        selected_values=(TraceValue("assessment_status", AssessmentStatus.NOT_ASSESSED.value),),
        candidates=candidates,
        findings=(finding,),
    )
    return ProtectionSelection(
        AssessmentStatus.NOT_ASSESSED,
        load,
        None,
        (finding,),
        decision,
    )
