"""Unit tests for the hover handler."""

from __future__ import annotations

from lsprotocol import types as lsp

from dlm_lsp.doc_state import DocumentState
from dlm_lsp.hover import compute_hover

_MINIMAL_DLM = """\
---
dlm_id: 01KPQ9M3000000000000000000
dlm_version: 15
base_model: smollm2-135m
---
Some prose.

::instruction::
### Q
What?
### A
That.
"""


def _state(text: str = _MINIMAL_DLM) -> DocumentState:
    return DocumentState(uri="file:///test.dlm", text=text)


class TestFrontmatterHover:
    def test_base_model_hover_shows_spec(self) -> None:
        result = compute_hover(_state(), lsp.Position(line=3, character=15))
        assert result is not None
        assert result.contents is not None
        assert isinstance(result.contents, lsp.MarkupContent)
        assert "smollm2-135m" in result.contents.value
        assert "Parameters" in result.contents.value

    def test_unknown_base_model_shows_warning(self) -> None:
        text = _MINIMAL_DLM.replace("smollm2-135m", "nonexistent-model")
        result = compute_hover(_state(text), lsp.Position(line=3, character=15))
        assert result is not None
        assert isinstance(result.contents, lsp.MarkupContent)
        assert "Unknown base model" in result.contents.value

    def test_hf_escape_hatch_shows_custom_label(self) -> None:
        text = _MINIMAL_DLM.replace("smollm2-135m", "hf:custom/model")
        state = _state(text)
        result = compute_hover(state, lsp.Position(line=3, character=15))
        assert result is not None
        assert isinstance(result.contents, lsp.MarkupContent)
        assert "Custom HF model" in result.contents.value

    def test_non_base_model_line_returns_none(self) -> None:
        result = compute_hover(_state(), lsp.Position(line=2, character=5))
        assert result is None


class TestBodyHover:
    def test_section_fence_hover(self) -> None:
        result = compute_hover(_state(), lsp.Position(line=7, character=5))
        assert result is not None
        assert isinstance(result.contents, lsp.MarkupContent)
        assert "instruction" in result.contents.value

    def test_prose_line_returns_none(self) -> None:
        result = compute_hover(_state(), lsp.Position(line=5, character=3))
        assert result is None


class TestEdgeCases:
    def test_cursor_past_end_returns_none(self) -> None:
        result = compute_hover(_state(), lsp.Position(line=999, character=0))
        assert result is None
