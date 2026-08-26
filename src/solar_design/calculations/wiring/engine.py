"""Pure wiring selections with explicit gaps and discrete cable allocation."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from solar_design.calculations._support import HUNDRED, rule_status_finding, stable_decision_id
from solar_design.domain import (
    AssessmentStatus,
    CandidateRecord,
    DecisionRecord,
    EngineeringValidationError,
    Finding,
    FindingSeverity,
    TraceValue,
    VerificationStatus,
)
from solar_design.models import (
    AmpacityRecord,
    CableSelection,
    CableSpec,
    ConduitAllocation,
    ConduitRun,
    ConduitSpec,
    PESelection,
    PESelectionRule,
    WiringSelection,
)
from solar_design.rules import DEFAULT_CONDUIT_FILL_LIMITS, RULES
from solar_design.validation import DecimalLike, require_positive

PI = Decimal("3.1415926535897932384626433832795028841971693993751")


def select_cable(
    required_table_ampacity_a: DecimalLike,
    cables: Sequence[CableSpec],
    ampacity_records: Sequence[AmpacityRecord],
    *,
    installation_method: str,
    current_carrying_conductors: int = 3,
    material: str | None = None,
    insulation: str | None = None,
    max_parallel_runs: int = 1,
) -> CableSelection:
    """Select the smallest total conductor area meeting table ampacity."""

    required = require_positive(required_table_ampacity_a, "required_table_ampacity_a")
    if not installation_method.strip():
        raise EngineeringValidationError("installation_method", "must not be blank")
    if current_carrying_conductors <= 0:
        raise EngineeringValidationError("current_carrying_conductors", "must be greater than zero")
    if max_parallel_runs <= 0:
        raise EngineeringValidationError("max_parallel_runs", "must be greater than zero")
    cable_by_id = {item.record_id: item for item in cables}
    if len(cable_by_id) != len(cables):
        raise EngineeringValidationError("cables", "contains duplicate record IDs")

    candidate_records: list[CandidateRecord] = []
    ranked: list[tuple[Decimal, int, Decimal, str, CableSpec, AmpacityRecord]] = []
    for record in ampacity_records:
        cable = cable_by_id.get(record.cable_id)
        reasons: list[str] = []
        if cable is None:
            reasons.append("ampacity record references an unknown cable")
        elif record.installation_method != installation_method:
            reasons.append("installation method does not match")
        elif record.current_carrying_conductors != current_carrying_conductors:
            reasons.append("current-carrying conductor count does not match")
        elif material is not None and cable.material.casefold() != material.casefold():
            reasons.append("conductor material does not match")
        elif insulation is not None and cable.insulation.casefold() != insulation.casefold():
            reasons.append("insulation does not match")
        if reasons:
            candidate_records.append(
                CandidateRecord(record.metadata.record_id, False, tuple(reasons))
            )
            continue
        assert cable is not None
        runs = next(
            (
                count
                for count in range(1, max_parallel_runs + 1)
                if record.ampacity_a * count >= required
            ),
            None,
        )
        if runs is None:
            candidate_records.append(
                CandidateRecord(
                    record.metadata.record_id,
                    False,
                    ("ampacity is insufficient within allowed parallel runs",),
                )
            )
            continue
        candidate_records.append(CandidateRecord(record.metadata.record_id, True, ()))
        ranked.append(
            (
                cable.cross_section_mm2 * runs,
                runs,
                cable.cross_section_mm2,
                cable.record_id,
                cable,
                record,
            )
        )

    findings: list[Finding] = []
    selected_cable: CableSpec | None = None
    selected_record: AmpacityRecord | None = None
    runs = 0
    total_ampacity: Decimal | None = None
    if ranked:
        _, runs, _, _, selected_cable, selected_record = min(ranked, key=lambda row: row[:4])
        total_ampacity = selected_record.ampacity_a * runs
        source_ids = tuple(
            dict.fromkeys((selected_cable.metadata.source_id, selected_record.metadata.source_id))
        )
        findings.extend(
            rule_status_finding(
                "CABLE-AMPACITY-TABLE",
                selected_record.metadata.verification_status,
                source_ids,
            )
        )
        if runs > 1:
            findings.append(
                Finding(
                    "PARALLEL_CABLE_POLICY_REVIEW",
                    "Parallel conductors require approved sharing, termination "
                    "and installation rules.",
                    FindingSeverity.WARNING,
                    VerificationStatus.UNKNOWN,
                    source_ids,
                )
            )
        status = AssessmentStatus.PASS
    else:
        source_ids = ()
        status = AssessmentStatus.MISSING
        findings.append(
            Finding(
                "NO_ELIGIBLE_CABLE",
                "No cable ampacity record satisfies the required current and mandatory filters.",
                FindingSeverity.BLOCKER,
                VerificationStatus.UNKNOWN,
            )
        )

    decision = DecisionRecord(
        stable_decision_id(
            "CABLE-SELECT", required, selected_cable.record_id if selected_cable else "NONE", runs
        ),
        "wiring",
        "CABLE-SELECT",
        "1.0",
        selected_record.metadata.verification_status
        if selected_record
        else VerificationStatus.UNKNOWN,
        (
            TraceValue("required_table_ampacity", required, "A"),
            TraceValue("installation_method", installation_method),
            TraceValue("current_carrying_conductors", current_carrying_conductors),
            TraceValue("max_parallel_runs", max_parallel_runs),
        ),
        calculated_values=(TraceValue("total_ampacity", total_ampacity, "A"),),
        selected_values=(
            TraceValue("cable_id", selected_cable.record_id if selected_cable else None),
            TraceValue("parallel_runs", runs),
        ),
        candidates=tuple(candidate_records),
        source_ids=source_ids,
        findings=tuple(findings),
    )
    return CableSelection(
        status,
        selected_cable.record_id if selected_cable else None,
        runs,
        selected_record.ampacity_a if selected_record else None,
        total_ampacity,
        tuple(findings),
        decision,
    )


def select_pe_conductor(
    phase_cross_section_mm2: DecimalLike,
    rules: Sequence[PESelectionRule],
    *,
    phase_material: str = "CU",
    pe_material: str = "CU",
) -> PESelection:
    """Use only an exact sourced phase-to-PE mapping; never extrapolate S/2."""

    phase_size = require_positive(phase_cross_section_mm2, "phase_cross_section_mm2")
    matches = [
        rule
        for rule in rules
        if rule.phase_cross_section_mm2 == phase_size
        and rule.phase_material.casefold() == phase_material.casefold()
        and rule.pe_material.casefold() == pe_material.casefold()
    ]
    source_ids: tuple[str, ...]
    if len(matches) > 1:
        raise EngineeringValidationError(
            "rules", "contains duplicate applicable PE mappings", phase_size
        )
    findings: list[Finding] = []
    if matches:
        rule = matches[0]
        pe_size: Decimal | None = rule.pe_cross_section_mm2
        status = AssessmentStatus.PASS
        source_ids = (rule.metadata.source_id,)
        verification_status = rule.metadata.verification_status
        findings.extend(rule_status_finding("PE-LOOKUP", verification_status, source_ids))
    else:
        pe_size = None
        status = AssessmentStatus.MISSING
        source_ids = ()
        verification_status = VerificationStatus.UNKNOWN
        findings.append(
            Finding(
                "PE_RULE_MISSING",
                "No exact sourced PE mapping exists for this phase conductor; "
                "no S/2 extrapolation was made.",
                FindingSeverity.WARNING,
                VerificationStatus.UNKNOWN,
                field="phase_cross_section_mm2",
            )
        )
    decision = DecisionRecord(
        stable_decision_id("PE-LOOKUP", phase_size, pe_size),
        "wiring",
        "PE-LOOKUP",
        RULES.get("PE-LOOKUP").version,
        verification_status,
        (
            TraceValue("phase_cross_section", phase_size, "mm²"),
            TraceValue("phase_material", phase_material),
            TraceValue("pe_material", pe_material),
        ),
        selected_values=(TraceValue("pe_cross_section", pe_size, "mm²"),),
        source_ids=source_ids,
        findings=tuple(findings),
    )
    return PESelection(status, phase_size, pe_size, tuple(findings), decision)


def select_cables_and_pe(
    required_table_ampacity_a: DecimalLike,
    cables: Sequence[CableSpec],
    ampacity_records: Sequence[AmpacityRecord],
    pe_rules: Sequence[PESelectionRule],
    *,
    installation_method: str,
    current_carrying_conductors: int = 3,
    material: str = "CU",
    insulation: str | None = None,
    max_parallel_runs: int = 1,
) -> WiringSelection:
    cable_result = select_cable(
        required_table_ampacity_a,
        cables,
        ampacity_records,
        installation_method=installation_method,
        current_carrying_conductors=current_carrying_conductors,
        material=material,
        insulation=insulation,
        max_parallel_runs=max_parallel_runs,
    )
    if cable_result.cable_id is None:
        missing = Finding(
            "PE_DEPENDS_ON_CABLE_SELECTION",
            "PE selection was not performed because no phase cable was selected.",
            FindingSeverity.WARNING,
            VerificationStatus.UNKNOWN,
        )
        pe_result = PESelection(
            AssessmentStatus.NOT_ASSESSED,
            Decimal("0"),
            None,
            (missing,),
            DecisionRecord(
                stable_decision_id("PE-LOOKUP", "NOT_ASSESSED"),
                "wiring",
                "PE-LOOKUP",
                "1.0",
                VerificationStatus.UNKNOWN,
                (),
                findings=(missing,),
            ),
        )
    else:
        selected = next(item for item in cables if item.record_id == cable_result.cable_id)
        pe_result = select_pe_conductor(
            selected.cross_section_mm2,
            pe_rules,
            phase_material=selected.material,
            pe_material=material,
        )
    not_assessed = (
        Finding(
            "VOLTAGE_DROP_NOT_ASSESSED",
            "Voltage drop is not assessed because approved route and limit rules are unavailable.",
            FindingSeverity.WARNING,
            VerificationStatus.UNKNOWN,
        ),
        Finding(
            "SHORT_CIRCUIT_NOT_ASSESSED",
            "Short-circuit withstand is not assessed because fault current and "
            "clearing time are unavailable.",
            FindingSeverity.WARNING,
            VerificationStatus.UNKNOWN,
        ),
    )
    return WiringSelection(cable_result, pe_result, findings=not_assessed)


def _fill_limit(cable_count: int) -> Decimal:
    if cable_count <= 0:
        raise EngineeringValidationError("cable_count", "must be greater than zero")
    return DEFAULT_CONDUIT_FILL_LIMITS[1 if cable_count == 1 else 2 if cable_count == 2 else 3]


def _find_discrete_assignment(
    cable_areas: tuple[Decimal, ...],
    conduit_area: Decimal,
    conduit_count: int,
) -> tuple[tuple[int, ...], ...] | None:
    """Find an exact integer cable-to-conduit assignment by backtracking."""

    ordered_indices = tuple(sorted(range(len(cable_areas)), key=lambda i: (-cable_areas[i], i)))
    bins: list[list[int]] = [[] for _ in range(conduit_count)]
    totals = [Decimal("0") for _ in range(conduit_count)]

    def search(position: int) -> bool:
        if position == len(ordered_indices):
            if any(not item for item in bins):
                return False
            return all(
                totals[i] <= conduit_area * _fill_limit(len(bins[i])) for i in range(conduit_count)
            )
        cable_index = ordered_indices[position]
        area = cable_areas[cable_index]
        seen_states: set[tuple[int, Decimal]] = set()
        for bin_index in range(conduit_count):
            state = (len(bins[bin_index]), totals[bin_index])
            if state in seen_states:
                continue
            seen_states.add(state)
            new_count = len(bins[bin_index]) + 1
            new_total = totals[bin_index] + area
            # A one-cable bin may use 53%; any bin that might reach 2+ cables
            # can never recover once its area exceeds 40%.
            optimistic_limit = (
                DEFAULT_CONDUIT_FILL_LIMITS[1] if new_count == 1 else DEFAULT_CONDUIT_FILL_LIMITS[3]
            )
            if new_total > conduit_area * optimistic_limit:
                continue
            bins[bin_index].append(cable_index)
            totals[bin_index] = new_total
            if search(position + 1):
                return True
            bins[bin_index].pop()
            totals[bin_index] -= area
            if not bins[bin_index]:
                break
        return False

    if not search(0):
        return None
    return tuple(tuple(sorted(item)) for item in bins)


def allocate_conduits(
    cable_outside_diameters_mm: Sequence[DecimalLike],
    conduits: Sequence[ConduitSpec],
    *,
    max_conduits: int | None = None,
) -> ConduitAllocation:
    """Allocate whole physical cables; fractional area splitting is impossible."""

    if not cable_outside_diameters_mm:
        raise EngineeringValidationError(
            "cable_outside_diameters_mm", "must contain at least one cable"
        )
    if not conduits:
        raise EngineeringValidationError("conduits", "must contain at least one conduit")
    diameters = tuple(
        require_positive(value, f"cable_outside_diameters_mm[{index}]")
        for index, value in enumerate(cable_outside_diameters_mm)
    )
    areas = tuple(PI * diameter * diameter / Decimal("4") for diameter in diameters)
    if max_conduits is None:
        max_runs = len(areas)
    elif max_conduits <= 0:
        raise EngineeringValidationError("max_conduits", "must be greater than zero")
    else:
        max_runs = min(max_conduits, len(areas))
    unique_ids = {item.record_id for item in conduits}
    if len(unique_ids) != len(conduits):
        raise EngineeringValidationError("conduits", "contains duplicate record IDs")
    ordered_conduits = sorted(
        conduits,
        key=lambda item: (item.internal_diameter_mm, item.record_id),
    )
    candidates: list[CandidateRecord] = []
    selected: ConduitSpec | None = None
    assignment: tuple[tuple[int, ...], ...] | None = None
    # Minimize number of parallel conduits first, then conduit diameter.
    for run_count in range(1, max_runs + 1):
        for conduit in ordered_conduits:
            conduit_area = PI * conduit.internal_diameter_mm**2 / Decimal("4")
            attempted = _find_discrete_assignment(areas, conduit_area, run_count)
            candidate_id = f"{conduit.record_id}x{run_count}"
            candidates.append(
                CandidateRecord(
                    candidate_id,
                    attempted is not None,
                    () if attempted is not None else ("no compliant integer cable allocation",),
                )
            )
            if attempted is not None:
                selected = conduit
                assignment = attempted
                break
        if selected is not None:
            break

    findings: list[Finding] = []
    runs: list[ConduitRun] = []
    if selected is None or assignment is None:
        status = AssessmentStatus.MISSING
        source_ids: tuple[str, ...] = ()
        findings.append(
            Finding(
                "NO_COMPLIANT_CONDUIT_ALLOCATION",
                "No conduit can contain all physical cables within the allowed "
                "run count and fill limits.",
                FindingSeverity.BLOCKER,
                VerificationStatus.UNKNOWN,
            )
        )
    else:
        status = AssessmentStatus.PASS
        source_ids = (selected.metadata.source_id,)
        conduit_area = PI * selected.internal_diameter_mm**2 / Decimal("4")
        for bin_indices in assignment:
            occupied = sum((areas[index] for index in bin_indices), Decimal("0"))
            limit = _fill_limit(len(bin_indices))
            runs.append(
                ConduitRun(
                    selected.record_id,
                    bin_indices,
                    len(bin_indices),
                    occupied,
                    conduit_area,
                    limit * HUNDRED,
                    occupied / conduit_area * HUNDRED,
                )
            )
        findings.extend(
            rule_status_finding("COND-FILL", selected.metadata.verification_status, source_ids)
        )
        if selected.is_screening_dimension:
            findings.append(
                Finding(
                    "CONDUIT_DIMENSION_SCREENING_ONLY",
                    "Conduit internal diameter is a screening value pending "
                    "certified manufacturer confirmation.",
                    FindingSeverity.WARNING,
                    selected.metadata.verification_status,
                    source_ids,
                )
            )
    decision = DecisionRecord(
        stable_decision_id(
            "COND-FILL", *diameters, selected.record_id if selected else "NONE", len(runs)
        ),
        "wiring",
        "COND-FILL",
        RULES.get("COND-FILL").version,
        selected.metadata.verification_status if selected else VerificationStatus.UNKNOWN,
        tuple(
            TraceValue(f"cable_{index + 1}_outside_diameter", value, "mm")
            for index, value in enumerate(diameters)
        ),
        calculated_values=(TraceValue("total_cable_area", sum(areas, Decimal("0")), "mm²"),),
        selected_values=(
            TraceValue("conduit_id", selected.record_id if selected else None),
            TraceValue("conduit_count", len(runs)),
        ),
        candidates=tuple(candidates),
        source_ids=source_ids,
        findings=tuple(findings),
    )
    return ConduitAllocation(
        status,
        selected.record_id if selected else None,
        tuple(runs),
        tuple(findings),
        decision,
    )
