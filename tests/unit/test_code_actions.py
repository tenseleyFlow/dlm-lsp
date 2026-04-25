"""Unit tests for the code action handler."""

from __future__ import annotations

from lsprotocol import types as lsp

from dlm_lsp.code_actions import compute_code_actions
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


def _range(line: int = 0) -> lsp.Range:
    return lsp.Range(
        start=lsp.Position(line=line, character=0),
        end=lsp.Position(line=line, character=0),
    )


class TestUnknownBaseModelAction:
    def test_suggests_closest_registry_key(self) -> None:
        text = _MINIMAL_DLM.replace("smollm2-135m", "smollm2-135")
        diag = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=3, character=0),
                end=lsp.Position(line=3, character=30),
            ),
            severity=lsp.DiagnosticSeverity.Warning,
            source="dlm-lsp",
            message="Unknown base model 'smollm2-135'",
        )
        actions = compute_code_actions(_state(text), _range(3), [diag])
        titles = [a.title for a in actions]
        assert any("smollm2-135m" in t for t in titles)

    def test_no_action_for_unrelated_diagnostic(self) -> None:
        diag = lsp.Diagnostic(
            range=_range(),
            severity=lsp.DiagnosticSeverity.Error,
            source="dlm-lsp",
            message="Something else entirely",
        )
        actions = compute_code_actions(_state(), _range(), [diag])
        assert actions == []


class TestMigrateAction:
    def test_no_migrate_when_current(self) -> None:
        actions = compute_code_actions(_state(), _range(), [])
        migrate_actions = [a for a in actions if "Migrate" in a.title]
        assert migrate_actions == []

    def test_migrate_offered_for_old_version(self) -> None:
        text = _MINIMAL_DLM.replace("dlm_version: 15", "dlm_version: 6")
        actions = compute_code_actions(_state(text), _range(), [])
        migrate_actions = [a for a in actions if "Migrate" in a.title]
        assert len(migrate_actions) == 1
        assert "v15" in migrate_actions[0].title
