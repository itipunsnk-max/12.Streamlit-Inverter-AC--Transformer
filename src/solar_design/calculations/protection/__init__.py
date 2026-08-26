"""Protection-device assessment boundary."""

from .catalogue import (
    protection_candidate_from_record,
    protection_candidates_from_records,
    protection_candidates_from_snapshot,
)
from .engine import select_protection

__all__ = [
    "protection_candidate_from_record",
    "protection_candidates_from_records",
    "protection_candidates_from_snapshot",
    "select_protection",
]
