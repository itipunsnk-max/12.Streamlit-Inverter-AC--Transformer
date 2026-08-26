"""Safe BOQ template evaluation using registered quantity functions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any

from .deltas import apply_boq_deltas, content_id
from .models import BOQBaseline, BOQDelta, BOQLine, BOQRevision, BOQTemplate

QuantityRule = Callable[[Mapping[str, Any], Mapping[str, Any]], Decimal]


class QuantityRuleRegistry:
    """Explicit allow-list of executable quantity policies; no expression eval."""

    def __init__(self, rules: Mapping[str, QuantityRule] | None = None) -> None:
        self._rules: dict[str, QuantityRule] = {
            "fixed": _fixed_quantity,
            "field": _field_quantity,
            "transformer_count": _transformer_count,
            "yard_lot": _yard_lot,
            "mdb_ground_rod": _mdb_ground_rod,
        }
        if rules:
            for key, rule in rules.items():
                self.register(key, rule)

    def register(self, key: str, rule: QuantityRule) -> None:
        normalized = key.strip()
        if not normalized:
            raise ValueError("quantity rule key must not be blank")
        self._rules[normalized] = rule

    def calculate(
        self,
        key: str,
        context: Mapping[str, Any],
        parameters: Mapping[str, Any],
    ) -> Decimal:
        try:
            rule = self._rules[key.strip()]
        except KeyError as exc:
            raise ValueError(f"unknown BOQ quantity rule {key!r}") from exc
        raw_result = rule(context, parameters)
        result = _decimal(raw_result, f"quantity rule {key!r}")
        if result < 0 or not result.is_finite():
            raise ValueError(f"quantity rule {key!r} returned invalid value {result!r}")
        return result


def generate_boq(
    design_run: Mapping[str, Any] | object,
    template: BOQTemplate,
    *,
    deltas: tuple[BOQDelta, ...] = (),
    quantity_rules: QuantityRuleRegistry | None = None,
) -> BOQRevision:
    """Generate a deterministic baseline, then reapply explicit user deltas."""

    baseline = generate_boq_baseline(
        design_run,
        template,
        quantity_rules=quantity_rules,
    )
    return apply_boq_deltas(baseline, deltas)


def generate_boq_baseline(
    design_run: Mapping[str, Any] | object,
    template: BOQTemplate,
    *,
    quantity_rules: QuantityRuleRegistry | None = None,
) -> BOQBaseline:
    """Generate only the deterministic baseline; user edits remain separate deltas."""

    context = _as_mapping(design_run)
    design_run_id = str(context.get("design_run_id") or context.get("run_id") or "unidentified")
    registry = quantity_rules or QuantityRuleRegistry()
    lines: list[BOQLine] = []
    for item in sorted(template.items, key=lambda value: (value.sort_order, value.item_id)):
        if not _conditions_match(context, item.conditions):
            continue
        quantity = registry.calculate(item.quantity_rule_key, context, item.quantity_parameters)
        if quantity == 0:
            continue
        lines.append(
            BOQLine(
                line_id=f"{template.template_id}:{item.item_id}",
                template_item_id=item.item_id,
                category=item.category,
                description_th=item.description_th,
                description_en=item.description_en,
                quantity=quantity,
                unit=item.unit,
                pricing_mode=item.pricing_mode,
                cost_status=item.cost_status,
                include_in_total=item.include_in_total,
                sort_order=item.sort_order,
                rate_id=item.rate_id,
                duplicate_scope_group=item.duplicate_scope_group,
                scope_tags=item.scope_tags,
                included_scope_tags=item.included_scope_tags,
                source_ids=item.source_ids,
                verification_status=item.verification_status,
                notes=item.notes,
            )
        )
    ordered_lines = tuple(sorted(lines, key=lambda value: (value.sort_order, value.line_id)))
    baseline_id = content_id(
        {
            "design_run_id": design_run_id,
            "template_id": template.template_id,
            "template_revision": template.revision,
            "lines": ordered_lines,
        },
        prefix="boqbase",
    )
    baseline = BOQBaseline(
        baseline_id=baseline_id,
        design_run_id=design_run_id,
        template_id=template.template_id,
        template_revision=template.revision,
        lines=ordered_lines,
    )
    return baseline


def _as_mapping(value: Mapping[str, Any] | object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return dumped
    raise TypeError("design_run must be a mapping, dataclass, or Pydantic model")


def _conditions_match(context: Mapping[str, Any], conditions: Mapping[str, Any]) -> bool:
    return all(_resolve_path(context, path) == expected for path, expected in conditions.items())


def _resolve_path(context: Mapping[str, Any], path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            raise ValueError(f"BOQ context field {path!r} is missing")
    return current


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _fixed_quantity(_: Mapping[str, Any], parameters: Mapping[str, Any]) -> Decimal:
    if "quantity" not in parameters:
        raise ValueError("fixed quantity rule requires 'quantity'")
    return _decimal(parameters["quantity"], "quantity")


def _field_quantity(context: Mapping[str, Any], parameters: Mapping[str, Any]) -> Decimal:
    path = str(parameters.get("path", ""))
    if not path:
        raise ValueError("field quantity rule requires 'path'")
    multiplier = _decimal(parameters.get("multiplier", 1), "multiplier")
    return _decimal(_resolve_path(context, path), path) * multiplier


def _transformer_count(context: Mapping[str, Any], _: Mapping[str, Any]) -> Decimal:
    for path in ("transformer.count", "transformer_selection.count", "transformer_count"):
        try:
            return _decimal(_resolve_path(context, path), path)
        except ValueError:
            continue
    raise ValueError("transformer count is missing from BOQ context")


def _yard_lot(context: Mapping[str, Any], _: Mapping[str, Any]) -> Decimal:
    installation = (
        str(
            context.get("installation_type")
            or _safe_resolve(context, "transformer.installation_type")
            or ""
        )
        .strip()
        .upper()
    )
    return Decimal("1") if installation in {"YARD", "TRANSFORMER_YARD"} else Decimal("0")


def _mdb_ground_rod(context: Mapping[str, Any], _: Mapping[str, Any]) -> Decimal:
    value = context.get("mdb_grounding_in_scope")
    if value is None:
        value = _safe_resolve(context, "grounding.mdb_in_scope")
    return Decimal("1") if value is True else Decimal("0")


def _safe_resolve(context: Mapping[str, Any], path: str) -> Any:
    try:
        return _resolve_path(context, path)
    except ValueError:
        return None
