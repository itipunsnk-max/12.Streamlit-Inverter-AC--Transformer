"""Seed policies transcribed from project references, never marked verified."""

from __future__ import annotations

from decimal import Decimal
from types import MappingProxyType

from solar_design.domain import FindingSeverity, VerificationStatus

from .registry import RuleDefinition, RuleRegistry

DEFAULT_CONDUIT_FILL_LIMITS = MappingProxyType(
    {
        1: Decimal("0.53"),
        2: Decimal("0.31"),
        3: Decimal("0.40"),  # key 3 means three or more physical cables
    }
)

DEFAULT_STANDARD_TRANSFORMER_RATINGS_KVA = tuple(
    Decimal(value)
    for value in (
        "30",
        "50",
        "100",
        "160",
        "250",
        "315",
        "400",
        "500",
        "630",
        "800",
        "1000",
        "1250",
        "1500",
        "1600",
        "2000",
        "2500",
        "3000",
    )
)

RULES = RuleRegistry(
    (
        RuleDefinition(
            "INV-DC-CAPACITY",
            "1.0",
            "catalogue_maximum_dc_power",
            VerificationStatus.MANUFACTURER_DATA,
            ("SRC-INV-001",),
            "Select inverter quantity from each model's explicit DC capacity.",
        ),
        RuleDefinition(
            "AC-CURRENT",
            "1.0",
            "ac_current_by_phase",
            VerificationStatus.ASSUMPTION,
            ("SRC-INV-001", "SRC-INV-002"),
            "Calculate AC current from real power, voltage, PF, efficiency and phase count.",
        ),
        RuleDefinition(
            "AMP-STRICT-70C",
            "1.0",
            "strict_terminal_temperature_conversion",
            VerificationStatus.DRAFT,
            ("SRC-AMP-003", "SRC-AMP-004"),
            "Convert load current to table ampacity for a strict terminal temperature limit.",
            FindingSeverity.WARNING,
        ),
        RuleDefinition(
            "COND-FILL",
            "1.0",
            "physical_cable_area_fill",
            VerificationStatus.DRAFT,
            ("SRC-WIR-003",),
            "Apply 53%, 31%, or 40% fill to one, two, or at least three cables.",
        ),
        RuleDefinition(
            "PE-LOOKUP",
            "1.0",
            "exact_phase_to_pe_lookup",
            VerificationStatus.DRAFT,
            ("SRC-WIR-002",),
            "Select PE cross-section only where an exact sourced mapping exists.",
            FindingSeverity.WARNING,
        ),
        RuleDefinition(
            "TX-SIZE-LOAD",
            "1.0",
            "load_demand_pf_spare_derating",
            VerificationStatus.DRAFT,
            ("SRC-TRF-001",),
            "Size transformer bank from load, demand, PF, spare and derating.",
        ),
        RuleDefinition(
            "TX-SIZE-PV",
            "1.0",
            "pv_pf_margin_derating",
            VerificationStatus.ASSUMPTION,
            ("SRC-TRF-001",),
            "Budgetary PV transformer sizing from inverter AC power, PF, margin and derating.",
            FindingSeverity.WARNING,
        ),
        RuleDefinition(
            "PROTECTION-PLACEHOLDER",
            "1.0",
            "not_assessed",
            VerificationStatus.UNKNOWN,
            ("SRC-INV-002",),
            "Protection coordination and interrupting duty are not assessed.",
            FindingSeverity.WARNING,
        ),
    )
)
