"""workspace/executeCommand handlers for frontmatter mutations."""

from __future__ import annotations

import logging
from typing import Any

from lsprotocol import types as lsp

from dlm_lsp.doc_state import StateStore

_log = logging.getLogger(__name__)

COMMAND_SET_BASE_MODEL = "dlm.setBaseModel"
COMMAND_ADD_SOURCE_DIRECTIVE = "dlm.addSourceDirective"

ALL_COMMANDS = [COMMAND_SET_BASE_MODEL, COMMAND_ADD_SOURCE_DIRECTIVE]


def execute_command(
    state_store: StateStore,
    command: str,
    arguments: list[Any] | None,
) -> lsp.WorkspaceEdit | None:
    if command == COMMAND_SET_BASE_MODEL:
        return _set_base_model(state_store, arguments or [])
    if command == COMMAND_ADD_SOURCE_DIRECTIVE:
        return _add_source_directive(state_store, arguments or [])
    _log.warning("unknown command: %s", command)
    return None


def _set_base_model(state_store: StateStore, arguments: list[Any]) -> lsp.WorkspaceEdit | None:
    if len(arguments) < 2:
        _log.warning("setBaseModel requires [uri, base_model_key]")
        return None

    uri: str = arguments[0]
    new_key: str = arguments[1]
    state = state_store.get(uri)
    if state is None:
        return None

    lines = state.text.splitlines(True)
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("base_model:"):
            indent = line[: len(line) - len(stripped)]
            new_line = f"{indent}base_model: {new_key}\n"
            return _single_line_edit(uri, i, line, new_line)

    return None


def _add_source_directive(
    state_store: StateStore, arguments: list[Any]
) -> lsp.WorkspaceEdit | None:
    if len(arguments) < 2:
        _log.warning("addSourceDirective requires [uri, relative_path]")
        return None

    uri: str = arguments[0]
    rel_path: str = arguments[1]
    state = state_store.get(uri)
    if state is None:
        return None

    lines = state.text.splitlines(True)
    sources_line = _find_sources_line(lines)
    training_line = _find_training_line(lines)
    closing_delim = _find_closing_frontmatter_delim(lines)

    new_entry = f"    - path: {rel_path}\n      include: ['**/*']\n"

    if sources_line is not None:
        insert_after = sources_line
        for j in range(sources_line + 1, len(lines)):
            stripped = lines[j].lstrip()
            if stripped.startswith("- path:") or stripped.startswith("- path :"):
                insert_after = j
                for k in range(j + 1, len(lines)):
                    inner = lines[k].lstrip()
                    if (
                        inner.startswith("include:")
                        or inner.startswith("exclude:")
                        or inner.startswith("max_")
                    ):
                        insert_after = k
                    else:
                        break
            elif (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith("include:")
                and not stripped.startswith("exclude:")
                and not stripped.startswith("max_")
            ):
                break
        return _insert_after_line(uri, insert_after, new_entry)

    if training_line is not None:
        sources_block = f"  sources:\n{new_entry}"
        return _insert_after_line(uri, training_line, sources_block)

    if closing_delim is not None:
        training_block = f"training:\n  sources:\n{new_entry}"
        return _insert_before_line(uri, closing_delim, training_block)

    return None


def _find_sources_line(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("sources:") and line.startswith("  "):
            return i
    return None


def _find_training_line(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if line.rstrip() == "training:" or line.startswith("training:"):
            return i
    return None


def _find_closing_frontmatter_delim(lines: list[str]) -> int | None:
    count = 0
    for i, line in enumerate(lines):
        if line.rstrip() == "---":
            count += 1
            if count == 2:
                return i
    return None


def _single_line_edit(uri: str, line_idx: int, old_line: str, new_line: str) -> lsp.WorkspaceEdit:
    return lsp.WorkspaceEdit(
        changes={
            uri: [
                lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(line=line_idx, character=0),
                        end=lsp.Position(line=line_idx, character=len(old_line.rstrip("\n"))),
                    ),
                    new_text=new_line.rstrip("\n"),
                )
            ]
        }
    )


def _insert_after_line(uri: str, line_idx: int, text: str) -> lsp.WorkspaceEdit:
    return lsp.WorkspaceEdit(
        changes={
            uri: [
                lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(line=line_idx + 1, character=0),
                        end=lsp.Position(line=line_idx + 1, character=0),
                    ),
                    new_text=text,
                )
            ]
        }
    )


def _insert_before_line(uri: str, line_idx: int, text: str) -> lsp.WorkspaceEdit:
    return lsp.WorkspaceEdit(
        changes={
            uri: [
                lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(line=line_idx, character=0),
                        end=lsp.Position(line=line_idx, character=0),
                    ),
                    new_text=text,
                )
            ]
        }
    )
