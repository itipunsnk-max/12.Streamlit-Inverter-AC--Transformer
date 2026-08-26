"""Controlled vocabularies used in calculations and audit records."""

from __future__ import annotations

from enum import StrEnum


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    DRAFT = "DRAFT"
    ASSUMPTION = "ASSUMPTION"
    MANUFACTURER_DATA = "MANUFACTURER_DATA"
    UTILITY_REQUIREMENT = "UTILITY_REQUIREMENT"
    REQUIRES_UTILITY_APPROVAL = "REQUIRES_UTILITY_APPROVAL"
    USER_OVERRIDE = "USER_OVERRIDE"
    UNKNOWN = "UNKNOWN"
    NOT_PERMITTED = "NOT_PERMITTED"


class FindingSeverity(StrEnum):
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"
    REVIEW = "REVIEW"
    INFO = "INFO"


class AssessmentStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_ASSESSED = "NOT_ASSESSED"
    MISSING = "MISSING"


class PhaseConfiguration(StrEnum):
    SINGLE_PHASE = "SINGLE_PHASE"
    THREE_PHASE = "THREE_PHASE"

    @property
    def conductors(self) -> int:
        return 1 if self is PhaseConfiguration.SINGLE_PHASE else 3


class TransformerDuty(StrEnum):
    EQUAL_SHARING = "EQUAL_SHARING"
    N_MINUS_ONE = "N_MINUS_ONE"
