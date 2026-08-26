"""Typed catalogue, request, and result models for engineering workflows."""

from .catalogue import (
    AmpacityRecord,
    BreakerSpec,
    CableSpec,
    ConduitSpec,
    InverterSpec,
    PESelectionRule,
    RecordMetadata,
    TransformerSpec,
)
from .results import (
    AmpacityAssessment,
    CableSelection,
    CircuitRequirement,
    ConduitAllocation,
    ConduitRun,
    InverterSelection,
    PESelection,
    ProtectionSelection,
    TransformerSelection,
    WiringSelection,
)

__all__ = [
    "AmpacityAssessment",
    "AmpacityRecord",
    "BreakerSpec",
    "CableSelection",
    "CableSpec",
    "CircuitRequirement",
    "ConduitAllocation",
    "ConduitRun",
    "ConduitSpec",
    "InverterSelection",
    "InverterSpec",
    "PESelection",
    "PESelectionRule",
    "ProtectionSelection",
    "RecordMetadata",
    "TransformerSelection",
    "TransformerSpec",
    "WiringSelection",
]
