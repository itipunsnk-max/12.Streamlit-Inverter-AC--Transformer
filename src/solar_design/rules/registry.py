"""Rule metadata registry; expressions are identifiers, never evaluated text."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from solar_design.domain import EngineeringValidationError, FindingSeverity, VerificationStatus


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    rule_id: str
    version: str
    expression_key: str
    verification_status: VerificationStatus
    source_ids: tuple[str, ...]
    description: str
    default_severity: FindingSeverity = FindingSeverity.REVIEW
    override_allowed: bool = True

    def __post_init__(self) -> None:
        for name in ("rule_id", "version", "expression_key", "description"):
            if not getattr(self, name).strip():
                raise EngineeringValidationError(name, "must not be blank")


class RuleRegistry:
    """Read-only lookup of reviewed rule identifiers.

    The registry deliberately stores no executable expression strings. The
    calculation modules map known ``expression_key`` values to reviewed Python
    functions, preventing arbitrary evaluation of data-file content.
    """

    def __init__(self, rules: tuple[RuleDefinition, ...]) -> None:
        by_id: dict[str, RuleDefinition] = {}
        for rule in rules:
            if rule.rule_id in by_id:
                raise EngineeringValidationError("rule_id", "must be unique", rule.rule_id)
            by_id[rule.rule_id] = rule
        self._rules: Mapping[str, RuleDefinition] = MappingProxyType(by_id)

    def get(self, rule_id: str) -> RuleDefinition:
        try:
            return self._rules[rule_id]
        except KeyError:
            raise EngineeringValidationError("rule_id", "is not registered", rule_id) from None

    def all(self) -> tuple[RuleDefinition, ...]:
        return tuple(self._rules.values())
