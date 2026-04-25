"""Unit tests for the diagnostics handler."""

from __future__ import annotations

from lsprotocol import types as lsp

from dlm_lsp.diagnostics import compute_diagnostics
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


class TestDiagnostics:
    def test_valid_dlm_produces_no_diagnostics(self) -> None:
        diags = compute_diagnostics(_state())
        assert diags == []

    def test_missing_frontmatter_delimiters(self) -> None:
        diags = compute_diagnostics(_state("just some text"))
        errors = [d for d in diags if d.severity == lsp.DiagnosticSeverity.Error]
        assert any("frontmatter delimiters" in (d.message or "") for d in errors)

    def test_single_delimiter_flagged(self) -> None:
        diags = compute_diagnostics(_state("---\nbase_model: x\n"))
        errors = [d for d in diags if d.severity == lsp.DiagnosticSeverity.Error]
        assert any("frontmatter delimiters" in (d.message or "") for d in errors)

    def test_parse_error_surfaced(self) -> None:
        bad = "---\ndlm_version: 999\n---\n"
        diags = compute_diagnostics(_state(bad))
        errors = [d for d in diags if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) >= 1

    def test_unknown_base_model_warns(self) -> None:
        text = _MINIMAL_DLM.replace("smollm2-135m", "not-a-real-model")
        diags = compute_diagnostics(_state(text))
        warnings = [d for d in diags if d.severity == lsp.DiagnosticSeverity.Warning]
        assert any("Unknown base model" in (d.message or "") for d in warnings)

    def test_hf_escape_hatch_no_warning(self) -> None:
        text = _MINIMAL_DLM.replace("smollm2-135m", "hf:custom/model")
        diags = compute_diagnostics(_state(text))
        warnings = [d for d in diags if d.severity == lsp.DiagnosticSeverity.Warning]
        assert not any("Unknown base model" in (d.message or "") for d in warnings)

    def test_empty_text_produces_no_diagnostics(self) -> None:
        diags = compute_diagnostics(_state(""))
        assert diags == []

    def test_diagnostics_dirty_flag_cleared(self) -> None:
        state = _state()
        assert state.diagnostics_dirty is True
        compute_diagnostics(state)
        assert state.diagnostics_dirty is False
