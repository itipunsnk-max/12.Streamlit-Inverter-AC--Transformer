"""Decimal-first input validation for deterministic calculations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from solar_design.domain.exceptions import EngineeringValidationError

DecimalLike = Decimal | int | str | float


def as_decimal(value: DecimalLike, field: str) -> Decimal:
    if isinstance(value, bool):
        raise EngineeringValidationError(field, "must be numeric", value)
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise EngineeringValidationError(field, "must be a finite decimal", value) from None
    if not result.is_finite():
        raise EngineeringValidationError(field, "must be finite", value)
    return result


def require_positive(value: DecimalLike, field: str) -> Decimal:
    result = as_decimal(value, field)
    if result <= 0:
        raise EngineeringValidationError(field, "must be greater than zero", value)
    return result


def require_non_negative(value: DecimalLike, field: str) -> Decimal:
    result = as_decimal(value, field)
    if result < 0:
        raise EngineeringValidationError(field, "must not be negative", value)
    return result


def require_between_zero_and_one(value: DecimalLike, field: str) -> Decimal:
    result = as_decimal(value, field)
    if result <= 0 or result > 1:
        raise EngineeringValidationError(field, "must be in the interval (0, 1]", value)
    return result
