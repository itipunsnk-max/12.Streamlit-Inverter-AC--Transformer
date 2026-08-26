"""Cable, protective-earth, and conduit allocation calculations."""

from .catalogue import (
    ampacity_record_for_cable,
    ampacity_records_for_cables,
    ampacity_records_from_snapshot,
    cable_spec_from_record,
    cable_specs_from_records,
    cable_specs_from_snapshot,
    conduit_spec_from_record,
    conduit_specs_from_records,
    conduit_specs_from_snapshot,
    pe_selection_rule_from_record,
    pe_selection_rules_from_records,
    pe_selection_rules_from_snapshot,
)
from .engine import (
    allocate_cable_conduits,
    allocate_conduits,
    select_cable,
    select_cables_and_pe,
    select_pe_conductor,
)

__all__ = [
    "allocate_cable_conduits",
    "allocate_conduits",
    "ampacity_record_for_cable",
    "ampacity_records_for_cables",
    "ampacity_records_from_snapshot",
    "cable_spec_from_record",
    "cable_specs_from_records",
    "cable_specs_from_snapshot",
    "conduit_spec_from_record",
    "conduit_specs_from_records",
    "conduit_specs_from_snapshot",
    "pe_selection_rule_from_record",
    "pe_selection_rules_from_records",
    "pe_selection_rules_from_snapshot",
    "select_cable",
    "select_cables_and_pe",
    "select_pe_conductor",
]
