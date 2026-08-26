"""Reusable validation helpers and public validation errors."""

from solar_design.domain.exceptions import (
    EngineeringValidationError,
    NoEligibleSelectionError,
)

from .numeric import (
    DecimalLike,
    as_decimal,
    require_between_zero_and_one,
    require_non_negative,
    require_positive,
)

__all__ = [
    "DecimalLike",
    "EngineeringValidationError",
    "NoEligibleSelectionError",
    "as_decimal",
    "require_between_zero_and_one",
    "require_non_negative",
    "require_positive",
]
