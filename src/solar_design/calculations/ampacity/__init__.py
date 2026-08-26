"""Cable ampacity and strict terminal-temperature checks."""

from .catalogue import (
    grouping_factor_from_record,
    grouping_factors_from_records,
    grouping_factors_from_snapshot,
    select_grouping_factor,
)
from .engine import check_70c_ampacity, strict_70c_required_ampacity

__all__ = [
    "check_70c_ampacity",
    "grouping_factor_from_record",
    "grouping_factors_from_records",
    "grouping_factors_from_snapshot",
    "select_grouping_factor",
    "strict_70c_required_ampacity",
]
