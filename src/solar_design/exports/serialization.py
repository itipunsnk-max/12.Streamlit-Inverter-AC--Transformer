"""Canonical conversion helpers shared by all export formats."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def to_primitive(value: Any) -> Any:
    """Convert domain values to deterministic JSON-safe primitives."""

    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite floating-point values cannot be exported")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal values cannot be exported")
        return format(value, "f")
    if isinstance(value, Enum):
        return to_primitive(value.value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((to_primitive(item) for item in value), key=_sort_key)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return to_primitive(model_dump(mode="python"))
    raise TypeError(f"unsupported export value type: {type(value).__name__}")


def canonical_json_bytes(value: Any, *, indent: int | None = 2) -> bytes:
    return json.dumps(
        to_primitive(value),
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    ).encode("utf-8")


def _sort_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
