"""pygls Language Server for .dlm files."""

from __future__ import annotations

import logging
from typing import Any

from lsprotocol import types as lsp
from pygls.server import LanguageServer

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
def _on_did_change(
    ls: DlmLanguageServer, params: lsp.DidChangeTextDocumentParams
) -> None:
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
def _on_hover(
    ls: DlmLanguageServer, params: lsp.HoverParams
) -> lsp.Hover | None:
    from dlm_lsp.hover import compute_hover

    state = ls.state.get(params.text_document.uri)
    if state is None:
        return None
    return compute_hover(state, params.position)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def _publish_diagnostics(ls: DlmLanguageServer, uri: str) -> None:
    from dlm_lsp.diagnostics import compute_diagnostics

    state = ls.state.get(uri)
    if state is None:
        return
    diags = compute_diagnostics(state)
    ls.publish_diagnostics(uri, diags)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    server.start_io()
