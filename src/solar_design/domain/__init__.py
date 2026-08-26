"""Core domain primitives shared by the engineering engines."""

from .audit import CandidateRecord, DecisionRecord, Finding, TraceValue
from .enums import (
    AssessmentStatus,
    FindingSeverity,
    PhaseConfiguration,
    TransformerDuty,
    VerificationStatus,
)
from .exceptions import EngineeringValidationError, NoEligibleSelectionError

__all__ = [
    "AssessmentStatus",
    "CandidateRecord",
    "DecisionRecord",
    "EngineeringValidationError",
    "Finding",
    "FindingSeverity",
    "NoEligibleSelectionError",
    "PhaseConfiguration",
    "TraceValue",
    "TransformerDuty",
    "VerificationStatus",
]
