"""Build the deterministic manifest for a CSV data release.

The manifest intentionally excludes itself.  It pins each CSV's bytes and
row count so the loader can reject a partial or modified release before any
calculation engine sees it.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "data" / "releases" / "2026.08-draft"
SCHEMA_VERSION = "1.0.0"


def csv_record_count(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header:
            raise ValueError(f"CSV has no header: {path.name}")
        return sum(1 for _ in reader)


def dataset_entry(path: Path) -> dict[str, int | str]:
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    return {
        "filename": path.name,
        "schema_version": SCHEMA_VERSION,
        "record_count": csv_record_count(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def build_manifest() -> dict[str, object]:
    files = {
        path.name: dataset_entry(path)
        for path in sorted(RELEASE_DIR.glob("*.csv"), key=lambda item: item.name)
    }
    source_count = csv_record_count(RELEASE_DIR / "sources.csv")
    return {
        "schema_version": SCHEMA_VERSION,
        "data_version": RELEASE_DIR.name,
        "release_status": "DRAFT",
        "release_date": date(2026, 8, 26).isoformat(),
        "application_compatibility": ">=0.1,<0.2",
        "allowed_verification_statuses": [
            "VERIFIED",
            "DRAFT",
            "ASSUMPTION",
            "MANUFACTURER_DATA",
            "UTILITY_REQUIREMENT",
            "REQUIRES_UTILITY_APPROVAL",
            "USER_OVERRIDE",
            "UNKNOWN",
            "NOT_PERMITTED",
        ],
        "files": files,
        "source_inventory_count": source_count,
        "approver_state": "PENDING_ENGINEERING_OWNER",
        "known_limitations": [
            "Reference extracts are incomplete and not suitable for construction issue.",
            "No engineering rule in this release is approved as VERIFIED.",
            "Manifest does not hash itself; its containing release commit is the audit anchor.",
        ],
    }


if __name__ == "__main__":
    manifest_path = RELEASE_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {manifest_path.relative_to(ROOT)}")
