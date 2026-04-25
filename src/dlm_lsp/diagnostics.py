"""textDocument/publishDiagnostics logic for .dlm files."""

from __future__ import annotations

import re

from lsprotocol import types as lsp

from dlm_lsp.doc_state import DocumentState

_FRONTMATTER_DELIM = re.compile(r"^---\s*$")


def compute_diagnostics(state: DocumentState) -> list[lsp.Diagnostic]:
    diags: list[lsp.Diagnostic] = []

    if not state.text.strip():
        return diags

    _check_frontmatter_delimiters(state, diags)
    _check_parse_errors(state, diags)
    _check_base_model(state, diags)

    state.diagnostics_dirty = False
    return diags


def _check_frontmatter_delimiters(
    state: DocumentState, diags: list[lsp.Diagnostic]
) -> None:
    lines = state.text.splitlines()
    delim_lines: list[int] = []
    for i, line in enumerate(lines):
        if _FRONTMATTER_DELIM.match(line):
            delim_lines.append(i)

    if len(delim_lines) < 2:
        diags.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                severity=lsp.DiagnosticSeverity.Error,
                source="dlm-lsp",
                message="Missing YAML frontmatter delimiters (---). A .dlm file must start with a YAML frontmatter block.",
            )
        )


def _check_parse_errors(state: DocumentState, diags: list[lsp.Diagnostic]) -> None:
    state.ensure_parsed()
    if state.parse_error:
        line = _extract_error_line(state.parse_error)
        diags.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=0),
                    end=lsp.Position(line=line, character=0),
                ),
                severity=lsp.DiagnosticSeverity.Error,
                source="dlm-lsp",
                message=state.parse_error,
            )
        )


def _check_base_model(state: DocumentState, diags: list[lsp.Diagnostic]) -> None:
    parsed = state.ensure_parsed()
    if parsed is None:
        return

    base_key = parsed.frontmatter.base_model
    if base_key.startswith("hf:"):
        return

    try:
        from dlm.base_models import BASE_MODELS

        if base_key not in BASE_MODELS:
            line = _find_base_model_line(state.text)
            diags.append(
                lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(line=line, character=0),
                        end=lsp.Position(line=line, character=100),
                    ),
                    severity=lsp.DiagnosticSeverity.Warning,
                    source="dlm-lsp",
                    message=f"Unknown base model '{base_key}'. Not found in the registry.",
                )
            )
    except ImportError:
        pass


def _find_base_model_line(text: str) -> int:
    for i, line in enumerate(text.splitlines()):
        if line.strip().startswith("base_model:"):
            return i
    return 0


def _extract_error_line(error_msg: str) -> int:
    m = re.search(r":(\d+):", error_msg)
    if m:
        return max(0, int(m.group(1)) - 1)
    return 0
