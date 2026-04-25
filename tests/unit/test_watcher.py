"""Unit tests for the manifest watcher."""

from __future__ import annotations

import time
from pathlib import Path

from dlm_lsp.watcher import ManifestWatcher, resolve_manifest_path


class TestManifestWatcher:
    def test_track_and_no_change(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        watcher = ManifestWatcher()
        watcher.track("file:///a.dlm", manifest)
        assert watcher.check_changed("file:///a.dlm") is False

    def test_detects_mtime_change(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        watcher = ManifestWatcher()
        watcher.track("file:///a.dlm", manifest)

        time.sleep(0.05)
        manifest.write_text('{"updated": true}')

        assert watcher.check_changed("file:///a.dlm") is True
        assert watcher.check_changed("file:///a.dlm") is False

    def test_untrack_stops_watching(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        watcher = ManifestWatcher()
        watcher.track("file:///a.dlm", manifest)
        watcher.untrack("file:///a.dlm")
        assert watcher.check_changed("file:///a.dlm") is False

    def test_check_unknown_uri(self) -> None:
        watcher = ManifestWatcher()
        assert watcher.check_changed("file:///unknown.dlm") is False

    def test_missing_file_tracked_then_created(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        watcher = ManifestWatcher()
        watcher.track("file:///a.dlm", manifest)
        assert watcher.check_changed("file:///a.dlm") is False

        manifest.write_text("{}")
        assert watcher.check_changed("file:///a.dlm") is True

    def test_check_all_changed(self, tmp_path: Path) -> None:
        m1 = tmp_path / "m1.json"
        m2 = tmp_path / "m2.json"
        m1.write_text("{}")
        m2.write_text("{}")
        watcher = ManifestWatcher()
        watcher.track("file:///a.dlm", m1)
        watcher.track("file:///b.dlm", m2)

        time.sleep(0.05)
        m1.write_text('{"v": 2}')

        changed = watcher.check_all_changed()
        assert "file:///a.dlm" in changed
        assert "file:///b.dlm" not in changed


class TestResolveManifestPath:
    def test_default_home(self) -> None:
        path = resolve_manifest_path("01ABC")
        assert path == Path.home() / ".dlm" / "store" / "01ABC" / "manifest.json"

    def test_custom_home(self, tmp_path: Path) -> None:
        path = resolve_manifest_path("01ABC", home=str(tmp_path))
        assert path == tmp_path / "store" / "01ABC" / "manifest.json"
