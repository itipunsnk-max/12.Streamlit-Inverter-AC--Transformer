"""Typed catalogue, request, and result models for engineering workflows."""

from .catalogue import (
    AmpacityRecord,
    BreakerSpec,
    CableSpec,
    ConduitSpec,
    CorrectionFactor,
    GroupingFactorSpec,
    InverterSpec,
    PESelectionRule,
    ProtectionCandidate,
    RecordMetadata,
    TransformerSpec,
)
from .manifest import DatasetManifestEntry, ReleaseManifest, ReleaseStatus
from .migrations import (
    DEFAULT_MIGRATIONS,
    MigrationRegistry,
    MigrationStep,
    SchemaMigrationError,
    SchemaVersion,
    migrate_payload,
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
from .schemas import (
    CURRENT_SCHEMA_VERSION,
    DATASET_MODELS,
    BOQTemplateRecord,
    BreakerRecord,
    DesignRuleRecord,
    GroupingFactorRecord,
    InverterRecord,
    PEMappingRecord,
    ReferenceRecord,
    SourceRecord,
    TransformerPriceRecord,
    TransformerRecord,
    UnitRateRecord,
)
from .schemas import (
    AmpacityRecord as AmpacityDataRecord,
)
from .schemas import (
    CableRecord as CableDataRecord,
)
from .schemas import (
    ConduitRecord as ConduitDataRecord,
)
from .snapshot import ReferenceSnapshot
from .units import Quantity, Unit

__all__ = [
    "AmpacityAssessment",
    "AmpacityDataRecord",
    "BOQTemplateRecord",
    "AmpacityRecord",
    "BreakerSpec",
    "BreakerRecord",
    "CableSelection",
    "CableDataRecord",
    "CableSpec",
    "CorrectionFactor",
    "CircuitRequirement",
    "ConduitAllocation",
    "ConduitRun",
    "ConduitSpec",
    "ConduitDataRecord",
    "CURRENT_SCHEMA_VERSION",
    "DATASET_MODELS",
    "DatasetManifestEntry",
    "DesignRuleRecord",
    "InverterSelection",
    "InverterSpec",
    "InverterRecord",
    "GroupingFactorRecord",
    "GroupingFactorSpec",
    "MigrationRegistry",
    "MigrationStep",
    "PEMappingRecord",
    "PESelection",
    "PESelectionRule",
    "ProtectionSelection",
    "ProtectionCandidate",
    "RecordMetadata",
    "ReferenceRecord",
    "ReferenceSnapshot",
    "ReleaseManifest",
    "ReleaseStatus",
    "Quantity",
    "SchemaMigrationError",
    "SchemaVersion",
    "SourceRecord",
    "TransformerSelection",
    "TransformerSpec",
    "TransformerPriceRecord",
    "TransformerRecord",
    "Unit",
    "UnitRateRecord",
    "WiringSelection",
    "DEFAULT_MIGRATIONS",
    "migrate_payload",
]
