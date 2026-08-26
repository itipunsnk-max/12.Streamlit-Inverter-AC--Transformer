"""Cable ampacity and strict terminal-temperature checks."""

from .engine import check_70c_ampacity, strict_70c_required_ampacity

__all__ = ["check_70c_ampacity", "strict_70c_required_ampacity"]
