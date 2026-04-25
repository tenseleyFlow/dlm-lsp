"""Unit tests for the completion handler."""

from __future__ import annotations

from lsprotocol import types as lsp

from dlm_lsp.completions import compute_completions
from dlm_lsp.doc_state import DocumentState

_MINIMAL_DLM = """\
---
dlm_id: 01KPQ9M3000000000000000000
dlm_version: 15
base_model: smollm2-135m
---
Some prose.

"""


def _state(text: str = _MINIMAL_DLM) -> DocumentState:
    return DocumentState(uri="file:///test.dlm", text=text)


class TestFrontmatterCompletions:
    def test_base_model_line_returns_registry_keys(self) -> None:
        result = compute_completions(_state(), lsp.Position(line=3, character=13))
        assert result is not None
        labels = {item.label for item in result.items}
        assert "smollm2-135m" in labels
        assert "qwen2.5-1.5b" in labels

    def test_base_model_completions_include_detail(self) -> None:
        result = compute_completions(_state(), lsp.Position(line=3, character=13))
        assert result is not None
        smol = next(i for i in result.items if i.label == "smollm2-135m")
        assert smol.detail is not None
        assert "135" in smol.detail or "0.1" in smol.detail

    def test_empty_frontmatter_line_returns_top_level_keys(self) -> None:
        text = "---\n\n---\nbody\n"
        result = compute_completions(_state(text), lsp.Position(line=1, character=0))
        assert result is not None
        labels = {item.label for item in result.items}
        assert "base_model:" in labels
        assert "training:" in labels


class TestBodyCompletions:
    def test_empty_body_line_returns_section_fences(self) -> None:
        result = compute_completions(_state(), lsp.Position(line=6, character=0))
        assert result is not None
        labels = {item.label for item in result.items}
        assert "::instruction::" in labels
        assert "::preference::" in labels
        assert "::image::" in labels
        assert "::audio::" in labels

    def test_section_fence_completions_are_snippets(self) -> None:
        result = compute_completions(_state(), lsp.Position(line=6, character=0))
        assert result is not None
        instr = next(i for i in result.items if i.label == "::instruction::")
        assert instr.insert_text_format == lsp.InsertTextFormat.Snippet
        assert "### Q" in (instr.insert_text or "")

    def test_non_empty_prose_line_returns_none(self) -> None:
        result = compute_completions(
            _state(),
            lsp.Position(line=5, character=5),  # "Some prose."
        )
        assert result is None


class TestEdgeCases:
    def test_cursor_past_end_returns_none(self) -> None:
        result = compute_completions(_state(), lsp.Position(line=999, character=0))
        assert result is None
