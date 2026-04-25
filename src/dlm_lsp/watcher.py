"""File system watcher for manifest changes and re-diagnostic triggers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass
class ManifestWatcher:
    """Tracks mtime of store manifest files to detect external changes.

    When ``dlm train`` completes outside the editor, the manifest updates.
    The watcher detects this and marks the associated document state dirty
    so diagnostics re-run on the next opportunity.
    """

    _tracked: dict[str, _TrackedManifest] = field(default_factory=dict)

    def track(self, uri: str, manifest_path: Path) -> None:
        mtime = _safe_mtime(manifest_path)
        self._tracked[uri] = _TrackedManifest(path=manifest_path, last_mtime=mtime)

    def untrack(self, uri: str) -> None:
        self._tracked.pop(uri, None)

    def check_changed(self, uri: str) -> bool:
        entry = self._tracked.get(uri)
        if entry is None:
            return False
        current = _safe_mtime(entry.path)
        if current is None:
            return False
        if entry.last_mtime is None or current > entry.last_mtime:
            entry.last_mtime = current
            return True
        return False

    def check_all_changed(self) -> list[str]:
        changed: list[str] = []
        for uri in list(self._tracked):
            if self.check_changed(uri):
                changed.append(uri)
        return changed


@dataclass
class _TrackedManifest:
    path: Path
    last_mtime: float | None = None


def _safe_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def resolve_manifest_path(dlm_id: str, home: str | None = None) -> Path:
    base = Path(home) if home else Path.home() / ".dlm"
    return base / "store" / dlm_id / "manifest.json"
