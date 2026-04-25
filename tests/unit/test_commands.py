"""Unit tests for workspace/executeCommand handlers."""

from __future__ import annotations

from dlm_lsp.commands import execute_command
from dlm_lsp.doc_state import StateStore

_DLM_WITH_TRAINING = """\
---
dlm_id: 01KPQ9M3000000000000000000
dlm_version: 15
base_model: smollm2-135m
training:
  adapter: lora
  lora_r: 16
---
Some prose.
"""

_DLM_WITH_SOURCES = """\
---
dlm_id: 01KPQ9M3000000000000000000
dlm_version: 15
base_model: smollm2-135m
training:
  adapter: lora
  sources:
    - path: existing/dir
      include: ['**/*.py']
---
Some prose.
"""

_MINIMAL_DLM = """\
---
dlm_id: 01KPQ9M3000000000000000000
dlm_version: 15
base_model: smollm2-135m
---
Some prose.
"""

_URI = "file:///test.dlm"


def _store(text: str = _MINIMAL_DLM) -> StateStore:
    s = StateStore()
    s.open(_URI, text)
    return s


class TestSetBaseModel:
    def test_replaces_base_model_line(self) -> None:
        edit = execute_command(_store(), "dlm.setBaseModel", [_URI, "qwen2.5-1.5b"])
        assert edit is not None
        assert edit.changes is not None
        edits = edit.changes[_URI]
        assert len(edits) == 1
        assert "qwen2.5-1.5b" in edits[0].new_text

    def test_missing_args_returns_none(self) -> None:
        assert execute_command(_store(), "dlm.setBaseModel", [_URI]) is None

    def test_unknown_uri_returns_none(self) -> None:
        assert execute_command(_store(), "dlm.setBaseModel", ["file:///other.dlm", "x"]) is None

    def test_preserves_indentation(self) -> None:
        text = _MINIMAL_DLM.replace("base_model:", "  base_model:")
        edit = execute_command(_store(text), "dlm.setBaseModel", [_URI, "phi-4"])
        assert edit is not None
        edits = edit.changes[_URI]  # type: ignore[union-attr]
        assert edits[0].new_text.startswith("  base_model:")


class TestAddSourceDirective:
    def test_appends_to_existing_sources(self) -> None:
        edit = execute_command(
            _store(_DLM_WITH_SOURCES), "dlm.addSourceDirective", [_URI, "new/dir"]
        )
        assert edit is not None
        edits = edit.changes[_URI]  # type: ignore[union-attr]
        assert any("new/dir" in e.new_text for e in edits)

    def test_creates_sources_under_training(self) -> None:
        edit = execute_command(
            _store(_DLM_WITH_TRAINING), "dlm.addSourceDirective", [_URI, "my/src"]
        )
        assert edit is not None
        edits = edit.changes[_URI]  # type: ignore[union-attr]
        combined = "".join(e.new_text for e in edits)
        assert "sources:" in combined
        assert "my/src" in combined

    def test_creates_training_block_when_missing(self) -> None:
        edit = execute_command(_store(_MINIMAL_DLM), "dlm.addSourceDirective", [_URI, "code/"])
        assert edit is not None
        edits = edit.changes[_URI]  # type: ignore[union-attr]
        combined = "".join(e.new_text for e in edits)
        assert "training:" in combined
        assert "sources:" in combined
        assert "code/" in combined

    def test_missing_args_returns_none(self) -> None:
        assert execute_command(_store(), "dlm.addSourceDirective", [_URI]) is None


class TestUnknownCommand:
    def test_unknown_command_returns_none(self) -> None:
        assert execute_command(_store(), "dlm.unknown", []) is None
