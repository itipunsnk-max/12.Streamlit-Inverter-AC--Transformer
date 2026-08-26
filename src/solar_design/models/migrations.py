"""Explicit, non-evaluating schema migration contract."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


class SchemaMigrationError(ValueError):
    """Raised when a payload cannot be safely migrated."""


@dataclass(frozen=True, order=True, slots=True)
class SchemaVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> SchemaVersion:
        parts = value.split(".")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise SchemaMigrationError(f"invalid schema version: {value!r}")
        return cls(*(int(part) for part in parts))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


MigrationFunction = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True, slots=True)
class MigrationStep:
    from_version: SchemaVersion
    to_version: SchemaVersion
    transform: MigrationFunction


class MigrationRegistry:
    """Allow-list of named version-to-version transformations."""

    def __init__(self, steps: tuple[MigrationStep, ...] = ()) -> None:
        self._steps: dict[tuple[SchemaVersion, SchemaVersion], MigrationFunction] = {}
        for step in steps:
            self.register(step)

    def register(self, step: MigrationStep) -> None:
        key = (step.from_version, step.to_version)
        if key in self._steps:
            raise SchemaMigrationError(
                f"duplicate migration: {step.from_version} -> {step.to_version}"
            )
        if step.to_version <= step.from_version:
            raise SchemaMigrationError("migration target must be newer than its source")
        self._steps[key] = step.transform

    def migrate(
        self,
        payload: Mapping[str, object],
        *,
        target_version: str,
    ) -> dict[str, object]:
        original = dict(payload)
        raw_version = original.get("schema_version")
        if not isinstance(raw_version, str):
            raise SchemaMigrationError("payload schema_version is required")
        current = SchemaVersion.parse(raw_version)
        target = SchemaVersion.parse(target_version)
        if current.major > target.major or (
            current.major == target.major and current.minor > target.minor
        ):
            raise SchemaMigrationError(f"future schema version is not supported: {current}")
        if current.major != target.major:
            raise SchemaMigrationError(f"no migration path from {current} to {target}")
        result = dict(original)
        while current.minor < target.minor:
            candidates = [
                (destination, function)
                for (source, destination), function in self._steps.items()
                if source == current and destination <= target
            ]
            if not candidates:
                raise SchemaMigrationError(f"no migration registered from {current}")
            destination, function = min(candidates, key=lambda item: item[0])
            result = dict(function(dict(result)))
            current = destination
            result["schema_version"] = str(current)
        if current.minor == target.minor and current.patch <= target.patch:
            result["schema_version"] = str(target)
            return result
        if current != target:
            raise SchemaMigrationError(f"no migration path from {current} to {target}")
        return result


DEFAULT_MIGRATIONS = MigrationRegistry()


def migrate_payload(
    payload: Mapping[str, object],
    *,
    target_version: str = "1.0.0",
    registry: MigrationRegistry = DEFAULT_MIGRATIONS,
) -> dict[str, object]:
    return registry.migrate(payload, target_version=target_version)
