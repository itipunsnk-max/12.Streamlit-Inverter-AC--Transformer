"""Session-independent workspace state and input coordinator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from solar_design.domain import Finding, FindingSeverity, TransformerDuty
from solar_design.models import ReferenceSnapshot
from solar_design.services.workflow import (
    ProjectInputs,
    WorkflowResults,
    load_reference_snapshot,
    run_design_workflow,
)
from solar_design.validation import EngineeringValidationError

WORKFLOW_STAGES = (
    "INVERTER",
    "PROTECTION",
    "AMPACITY",
    "WIRING",
    "TRANSFORMER",
    "BOQ",
    "COST",
)

__all__ = [
    "WORKFLOW_STAGES",
    "ProjectInputs",
    "WorkspaceCoordinator",
    "WorkspaceState",
]


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    """The single aggregate stored in ``st.session_state``."""

    release_dir: str
    reference_snapshot: ReferenceSnapshot | None
    reference_error: str | None
    inverter_options: tuple[tuple[str, str], ...]
    inputs: ProjectInputs
    results: WorkflowResults = WorkflowResults()
    stale_stages: frozenset[str] = frozenset(WORKFLOW_STAGES)
    validation_errors: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()
    override_reasons: tuple[tuple[str, str], ...] = ()
    revision: int = 0
    updated_at: date | None = None

    def stage_is_stale(self, stage: str) -> bool:
        return stage.upper() in self.stale_stages

    @property
    def has_blocker(self) -> bool:
        return any(item.severity is FindingSeverity.BLOCKER for item in self.findings)


class WorkspaceCoordinator:
    """Validate user inputs and delegate engineering work to the service layer."""

    def __init__(self, release_dir: str | Path) -> None:
        self.release_dir = Path(release_dir).resolve()

    def initial_state(self) -> WorkspaceState:
        try:
            snapshot, inverter_options = load_reference_snapshot(self.release_dir)
            return WorkspaceState(
                release_dir=str(self.release_dir),
                reference_snapshot=snapshot,
                reference_error=None,
                inverter_options=inverter_options,
                inputs=ProjectInputs(),
                updated_at=date.today(),
            )
        except (OSError, ValueError) as exc:
            return WorkspaceState(
                release_dir=str(self.release_dir),
                reference_snapshot=None,
                reference_error=f"Reference release could not be loaded: {exc}",
                inverter_options=(),
                inputs=ProjectInputs(),
                validation_errors=("Reference data is unavailable; calculation is blocked.",),
                updated_at=date.today(),
            )

    def save_inputs(
        self,
        state: WorkspaceState,
        values: Mapping[str, Any],
    ) -> WorkspaceState:
        inputs, errors = self.parse_inputs(values)
        if errors:
            return replace(state, validation_errors=errors)
        if inputs == state.inputs:
            return replace(state, validation_errors=())
        return replace(
            state,
            inputs=inputs,
            stale_stages=frozenset(WORKFLOW_STAGES),
            validation_errors=(),
            findings=(),
            override_reasons=_override_reasons(inputs),
            revision=state.revision + 1,
            updated_at=date.today(),
        )

    def parse_inputs(
        self,
        values: Mapping[str, Any],
    ) -> tuple[ProjectInputs, tuple[str, ...]]:
        errors: list[str] = []
        project_name = str(values.get("project_name", "")).strip()
        if not project_name:
            errors.append("Project name is required.")

        def decimal_field(key: str, label: str, *, optional: bool = False) -> Decimal | None:
            raw = values.get(key)
            if optional and (raw is None or str(raw).strip() == ""):
                return None
            try:
                value = raw if isinstance(raw, Decimal) else Decimal(str(raw))
            except (InvalidOperation, ValueError, TypeError):
                errors.append(f"{label} must be a decimal number.")
                return None
            if not value.is_finite():
                errors.append(f"{label} must be finite.")
                return None
            return value

        required_dc = decimal_field("required_dc_power_kwp", "Required DC power")
        ac_voltage = decimal_field("required_ac_voltage_v", "AC voltage", optional=True)
        load_kw = decimal_field("load_kw", "Load")
        power_factor = decimal_field("power_factor", "Power factor")
        demand_factor = decimal_field("demand_factor", "Demand factor")
        spare_percent = decimal_field("spare_percent", "Spare percent")
        derating_factor = decimal_field("derating_factor", "Derating factor")
        high_voltage = decimal_field("high_voltage_v", "HV voltage")
        low_voltage = decimal_field("low_voltage_v", "LV voltage")
        transformer_override = decimal_field(
            "override_transformer_rating_kva",
            "Transformer override rating",
            optional=True,
        )

        for value, label in (
            (required_dc, "Required DC power"),
            (load_kw, "Load"),
            (high_voltage, "HV voltage"),
            (low_voltage, "LV voltage"),
        ):
            if value is not None and value <= 0:
                errors.append(f"{label} must be greater than zero.")
        for value, label in (
            (power_factor, "Power factor"),
            (demand_factor, "Demand factor"),
            (derating_factor, "Derating factor"),
        ):
            if value is not None and not Decimal("0") < value <= Decimal("1"):
                errors.append(f"{label} must be greater than 0 and at most 1.")
        if ac_voltage is not None and ac_voltage <= 0:
            errors.append("AC voltage must be greater than zero when supplied.")
        if spare_percent is not None and spare_percent < 0:
            errors.append("Spare percent must not be negative.")
        if transformer_override is not None and transformer_override < 0:
            errors.append("Transformer override rating must not be negative.")

        try:
            transformer_count = int(values.get("transformer_count", 0))
        except (TypeError, ValueError):
            transformer_count = 0
            errors.append("Transformer count must be a whole number.")
        if transformer_count <= 0:
            errors.append("Transformer count must be greater than zero.")

        installation_type = str(values.get("installation_type", "")).strip().upper()
        if installation_type not in {"YARD", "POLE_MOUNTED"}:
            errors.append("Installation type is not supported by the current workflow.")
        try:
            duty = TransformerDuty(str(values.get("duty", "")).strip().upper())
        except ValueError:
            errors.append("Transformer duty is invalid.")
            duty = TransformerDuty.EQUAL_SHARING
        if duty is TransformerDuty.N_MINUS_ONE and transformer_count < 2:
            errors.append("N-1 duty requires at least two transformers.")

        override_inverter = str(values.get("override_inverter_model_id") or "").strip() or None
        override_reason = str(values.get("override_reason") or "").strip() or None
        if (override_inverter or transformer_override is not None) and not override_reason:
            errors.append("An override reason is required for every manual override.")
        if transformer_override == Decimal("0"):
            transformer_override = None

        inputs = ProjectInputs(
            project_name=project_name,
            required_dc_power_kwp=required_dc or Decimal("0"),
            required_ac_voltage_v=ac_voltage,
            load_kw=load_kw or Decimal("0"),
            power_factor=power_factor or Decimal("0"),
            demand_factor=demand_factor or Decimal("0"),
            spare_percent=spare_percent or Decimal("0"),
            derating_factor=derating_factor or Decimal("0"),
            installation_type=installation_type or "YARD",
            transformer_count=transformer_count,
            duty=duty,
            high_voltage_v=high_voltage or Decimal("0"),
            low_voltage_v=low_voltage or Decimal("0"),
            override_inverter_model_id=override_inverter,
            override_transformer_rating_kva=transformer_override,
            override_reason=override_reason,
        )
        return inputs, tuple(errors)

    def run_workflow(self, state: WorkspaceState) -> WorkspaceState:
        if state.reference_snapshot is None:
            return replace(
                state,
                validation_errors=("Reference data is unavailable; calculation is blocked.",),
            )
        if state.validation_errors:
            return state
        try:
            results = run_design_workflow(
                state.inputs,
                state.reference_snapshot,
                state.revision,
            )
        except (EngineeringValidationError, ValueError) as exc:
            return replace(
                state,
                validation_errors=(f"Workflow validation failed: {exc}",),
                stale_stages=frozenset(WORKFLOW_STAGES),
            )
        findings = _collect_findings(results)
        return replace(
            state,
            results=results,
            stale_stages=frozenset(),
            validation_errors=(),
            findings=findings,
            override_reasons=_override_reasons(state.inputs),
            updated_at=date.today(),
        )


def _override_reasons(inputs: ProjectInputs) -> tuple[tuple[str, str], ...]:
    if not inputs.override_reason:
        return ()
    reasons: list[tuple[str, str]] = []
    if inputs.override_inverter_model_id:
        reasons.append(("INVERTER", inputs.override_reason))
    if inputs.override_transformer_rating_kva is not None:
        reasons.append(("TRANSFORMER", inputs.override_reason))
    return tuple(reasons)


def _collect_findings(results: WorkflowResults) -> tuple[Finding, ...]:
    candidates: list[Finding] = []
    for result in (
        results.inverter,
        results.protection,
        results.ampacity,
        results.wiring,
        results.conduit,
        results.transformer,
    ):
        if result is not None:
            candidates.extend(result.findings)
    if results.wiring is not None:
        candidates.extend(results.wiring.cable.findings)
        candidates.extend(results.wiring.protective_earth.findings)
    if results.boq is not None:
        candidates.extend(results.boq.findings)
    if results.cost is not None:
        candidates.extend(results.cost.findings)
    unique: dict[tuple[Any, ...], Finding] = {}
    for finding in candidates:
        key = (
            finding.code,
            finding.message,
            finding.severity,
            finding.verification_status,
            finding.source_ids,
            finding.field,
        )
        unique[key] = finding
    return tuple(unique.values())
