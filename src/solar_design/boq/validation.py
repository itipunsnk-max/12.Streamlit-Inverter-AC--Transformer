"""Commercial-scope checks that do not reinterpret engineering design rules."""

from __future__ import annotations

from collections import defaultdict

from solar_design.domain import Finding, FindingSeverity, VerificationStatus

from .models import BOQLine


def find_duplicate_scopes(lines: tuple[BOQLine, ...]) -> tuple[Finding, ...]:
    """Return deterministic warnings for duplicated or already-included scope.

    A duplicate group identifies mutually overlapping priced lines.  Scope tags
    capture inclusion language such as a transformer quote that already includes
    ``crane`` while another active BOQ line separately prices crane work.
    """

    active = tuple(line for line in lines if line.is_effectively_included)
    findings: list[Finding] = []

    grouped: dict[str, list[BOQLine]] = defaultdict(list)
    for line in active:
        if line.duplicate_scope_group:
            grouped[line.duplicate_scope_group.strip().lower()].append(line)
    for group, members in sorted(grouped.items()):
        if len(members) > 1:
            ids = tuple(sorted(line.line_id for line in members))
            findings.append(
                Finding(
                    code="BOQ_DUPLICATE_SCOPE_GROUP",
                    message=f"Active BOQ lines {', '.join(ids)} share scope group '{group}'.",
                    severity=FindingSeverity.WARNING,
                    verification_status=VerificationStatus.UNKNOWN,
                    source_ids=tuple(
                        sorted({source for line in members for source in line.source_ids})
                    ),
                )
            )

    seen: set[tuple[str, str, str]] = set()
    for including_line in sorted(active, key=lambda item: item.line_id):
        included_tags = set(including_line.included_scope_tags)
        if not included_tags:
            continue
        for priced_line in sorted(active, key=lambda item: item.line_id):
            if including_line.line_id == priced_line.line_id:
                continue
            overlap = included_tags.intersection(priced_line.scope_tags)
            for tag in sorted(overlap):
                key = (including_line.line_id, priced_line.line_id, tag)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        code="BOQ_INCLUDED_SCOPE_OVERLAP",
                        message=(
                            f"'{including_line.line_id}' includes '{tag}', which is also priced "
                            f"by active line '{priced_line.line_id}'."
                        ),
                        severity=FindingSeverity.WARNING,
                        verification_status=VerificationStatus.UNKNOWN,
                        source_ids=tuple(
                            sorted(set(including_line.source_ids + priced_line.source_ids))
                        ),
                    )
                )
    return tuple(findings)
