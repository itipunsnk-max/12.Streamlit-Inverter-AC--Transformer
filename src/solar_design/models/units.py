"""Controlled engineering units and immutable quantities.

The calculation engines use ``Decimal`` values directly.  This module gives
the data-contract layer a small, explicit unit vocabulary without allowing
unit labels from CSV files to become executable behavior.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class Unit(StrEnum):
    AMPERE = "A"
    CELSIUS = "degC"
    KILOVOLT_AMPERE = "kVA"
    KILOWATT = "kW"
    KILOWATT_PEAK = "kWp"
    METRE = "m"
    MILLIMETRE = "mm"
    MILLIMETRE_SQUARED = "mm2"
    PERCENT = "%"
    THB = "THB"
    VOLT = "V"


class Quantity(BaseModel):
    """A finite, immutable Decimal value with an explicit unit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: Decimal
    unit: Unit

    @field_validator("value")
    @classmethod
    def _finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("quantity value must be finite")
        return value
