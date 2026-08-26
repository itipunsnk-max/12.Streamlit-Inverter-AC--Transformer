"""Validated access to an immutable reference-data release."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


class DataReleaseError(ValueError):
    """Raised when reference data is missing, malformed, or has the wrong hash."""


class ReleaseRepository:
    """Read a versioned release without leaking filesystem concerns into engines."""

    def __init__(self, release_dir: str | Path) -> None:
        self.release_dir = Path(release_dir).resolve()
        self.manifest = self._load_manifest()

    @property
    def data_version(self) -> str:
        return str(self.manifest["data_version"])

    def _load_manifest(self) -> dict[str, Any]:
        path = self.release_dir / "manifest.json"
        if not path.is_file():
            raise DataReleaseError(f"Missing release manifest: {path}")
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataReleaseError(f"Invalid release manifest: {exc}") from exc
        for field in ("schema_version", "data_version"):
            if not manifest.get(field):
                raise DataReleaseError(f"Manifest field is required: {field}")
        return manifest

    def load_csv(self, filename: str) -> list[dict[str, str]]:
        path = (self.release_dir / filename).resolve()
        if path.parent != self.release_dir or not path.is_file():
            raise DataReleaseError(f"Dataset is not available in this release: {filename}")
        self._verify_declared_hash(filename, path)
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        except (OSError, csv.Error) as exc:
            raise DataReleaseError(f"Cannot read dataset {filename}: {exc}") from exc

    def _verify_declared_hash(self, filename: str, path: Path) -> None:
        files = self.manifest.get("files", {})
        entry = files.get(filename) if isinstance(files, dict) else None
        expected = entry.get("sha256") if isinstance(entry, dict) else None
        if not expected:
            return
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != str(expected).lower():
            raise DataReleaseError(f"Hash mismatch for {filename}")

    def snapshot(self) -> dict[str, Any]:
        """Return immutable-identifying metadata for project exports and audit records."""

        return {
            "schema_version": self.manifest["schema_version"],
            "data_version": self.manifest["data_version"],
            "release_date": self.manifest.get("release_date"),
            "approval_status": self.manifest.get("approval_status", "DRAFT"),
            "files": self.manifest.get("files", {}),
        }
