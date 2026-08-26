"""Exceptions raised for hard-invalid engineering inputs."""

from __future__ import annotations


class EngineeringValidationError(ValueError):
    """An input is structurally or physically invalid.

    Unverified engineering rules do not raise this exception; they produce
    findings. This exception is reserved for values that cannot be calculated
    safely, such as non-positive voltage or a power factor outside (0, 1].
    """

    def __init__(self, field: str, message: str, value: object | None = None) -> None:
        self.field = field
        self.value = value
        suffix = "" if value is None else f" (received {value!r})"
        super().__init__(f"{field}: {message}{suffix}")


class NoEligibleSelectionError(EngineeringValidationError):
    """No catalogue item can meet a mandatory selection constraint."""
