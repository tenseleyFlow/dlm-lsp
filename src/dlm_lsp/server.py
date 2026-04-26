"""pygls Language Server for .dlm files."""

from __future__ import annotations

import logging
from typing import Any

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from dlm_lsp.capabilities import (
    COMPLETION_TRIGGER_CHARACTERS,
    SERVER_NAME,
    SERVER_VERSION,
)
from dlm_lsp.doc_state import StateStore

_log = logging.getLogger(__name__)


class DlmLanguageServer(LanguageServer):
    """LSP server for .dlm document authoring."""

    def __init__(self) -> None:
        super().__init__(SERVER_NAME, SERVER_VERSION)
        self.state = StateStore()


server = DlmLanguageServer()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@server.feature(lsp.INITIALIZED)
def _on_initialized(ls: DlmLanguageServer, params: lsp.InitializedParams) -> None:
    _log.info("dlm-lsp initialized")


# ---------------------------------------------------------------------------
# Document sync
# ---------------------------------------------------------------------------


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def _on_did_open(ls: DlmLanguageServer, params: lsp.DidOpenTextDocumentParams) -> None:
    uri = params.text_document.uri
    text = params.text_document.text
    version = params.text_document.version
    ls.state.open(uri, text, version)
    _publish_diagnostics(ls, uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def _on_did_change(ls: DlmLanguageServer, params: lsp.DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    version = params.text_document.version
    if params.content_changes:
        text = params.content_changes[-1].text
        ls.state.update(uri, text, version)
        _publish_diagnostics(ls, uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def _on_did_close(ls: DlmLanguageServer, params: lsp.DidCloseTextDocumentParams) -> None:
    ls.state.close(params.text_document.uri)


# ---------------------------------------------------------------------------
# Completions
# ---------------------------------------------------------------------------


@server.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=COMPLETION_TRIGGER_CHARACTERS),
)
def _on_completion(
    ls: DlmLanguageServer, params: lsp.CompletionParams
) -> lsp.CompletionList | None:
    from dlm_lsp.completions import compute_completions

    state = ls.state.get(params.text_document.uri)
    if state is None:
        return None
    return compute_completions(state, params.position)


# ---------------------------------------------------------------------------
# Hover
# ---------------------------------------------------------------------------


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def _on_hover(ls: DlmLanguageServer, params: lsp.HoverParams) -> lsp.Hover | None:
    from dlm_lsp.hover import compute_hover

    state = ls.state.get(params.text_document.uri)
    if state is None:
        return None
    return compute_hover(state, params.position)


# ---------------------------------------------------------------------------
# Code actions
# ---------------------------------------------------------------------------


@server.feature(
    lsp.TEXT_DOCUMENT_CODE_ACTION,
    lsp.CodeActionOptions(
        code_action_kinds=[lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.Source]
    ),
)
def _on_code_action(
    ls: DlmLanguageServer, params: lsp.CodeActionParams
) -> list[lsp.CodeAction] | None:
    from dlm_lsp.code_actions import compute_code_actions

    state = ls.state.get(params.text_document.uri)
    if state is None:
        return None
    return compute_code_actions(state, params.range, params.context.diagnostics)


# ---------------------------------------------------------------------------
# Commands (all via @server.command so pygls dispatches naturally)
# ---------------------------------------------------------------------------


@server.command("dlm.setBaseModel")
def _cmd_set_base_model(ls: DlmLanguageServer, *args: Any) -> None:
    from dlm_lsp.commands import execute_command

    edit = execute_command(ls.state, "dlm.setBaseModel", list(args))
    if edit is not None:
        ls.workspace_apply_edit(lsp.ApplyWorkspaceEditParams(edit=edit))


@server.command("dlm.addSourceDirective")
def _cmd_add_source(ls: DlmLanguageServer, *args: Any) -> None:
    from dlm_lsp.commands import execute_command

    edit = execute_command(ls.state, "dlm.addSourceDirective", list(args))
    if edit is not None:
        ls.workspace_apply_edit(lsp.ApplyWorkspaceEditParams(edit=edit))


# ---------------------------------------------------------------------------
# Custom requests (side panel data feeds)
# ---------------------------------------------------------------------------


@server.command("dlm/listBaseModels")
def _list_base_models(ls: DlmLanguageServer, *args: Any) -> list[dict[str, Any]]:
    try:
        from dlm.base_models import BASE_MODELS

        return [
            {
                "key": spec.key,
                "hf_id": spec.hf_id,
                "params": spec.params,
                "size_gb_fp16": spec.size_gb_fp16,
                "context_length": spec.context_length,
                "modality": spec.modality,
                "license_spdx": spec.license_spdx,
                "requires_acceptance": spec.requires_acceptance,
            }
            for spec in BASE_MODELS.values()
        ]
    except ImportError:
        return []


@server.command("dlm/listTemplates")
def _list_templates(ls: DlmLanguageServer, *args: Any) -> list[dict[str, Any]]:
    try:
        from dlm.templates.registry import list_bundled

        return [
            {
                "name": t.name,
                "title": t.title,
                "domain_tags": list(t.domain_tags),
                "recommended_base": t.recommended_base,
                "summary": t.summary,
                "sample_prompts": list(t.sample_prompts),
            }
            for t in list_bundled()
        ]
    except ImportError:
        return []


@server.command("dlm/documentState")
def _document_state(ls: DlmLanguageServer, *args: Any) -> dict[str, Any] | None:
    if not args:
        return None
    uri: str = args[0]
    state = ls.state.get(uri)
    if state is None:
        return None
    parsed = state.ensure_parsed()
    if parsed is None:
        return {"uri": uri, "error": state.parse_error}
    spec = state.ensure_base_model_spec()
    fm = parsed.frontmatter
    section_counts: dict[str, int] = {}
    for section in parsed.sections:
        key = section.type.value.lower()
        section_counts[key] = section_counts.get(key, 0) + 1
    return {
        "uri": uri,
        "dlm_id": fm.dlm_id,
        "dlm_version": fm.dlm_version,
        "base_model": fm.base_model,
        "base_model_spec": spec,
        "section_counts": section_counts,
    }


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def _publish_diagnostics(ls: DlmLanguageServer, uri: str) -> None:
    from dlm_lsp.diagnostics import compute_diagnostics

    state = ls.state.get(uri)
    if state is None:
        return
    diags = compute_diagnostics(state)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diags)
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    server.start_io()
