"""textDocument/codeAction handler for .dlm files."""

from __future__ import annotations

from collections.abc import Sequence

from lsprotocol import types as lsp

from dlm_lsp.doc_state import DocumentState


def compute_code_actions(
    state: DocumentState,
    range_: lsp.Range,
    diagnostics: Sequence[lsp.Diagnostic],
) -> list[lsp.CodeAction]:
    actions: list[lsp.CodeAction] = []

    for diag in diagnostics:
        if "Unknown base model" in (diag.message or ""):
            action = _suggest_closest_base_model(state, diag)
            if action is not None:
                actions.append(action)

        if "newer than this parser" in (diag.message or ""):
            actions.append(
                lsp.CodeAction(
                    title="Run `dlm migrate` to update schema",
                    kind=lsp.CodeActionKind.QuickFix,
                    diagnostics=[diag],
                    command=lsp.Command(
                        title="dlm migrate",
                        command="dlm.runInTerminal",
                        arguments=["dlm", "migrate", "--dry-run"],
                    ),
                )
            )

    raw_version = _extract_raw_dlm_version(state.text)
    if raw_version is not None:
        from dlm.doc.schema import CURRENT_SCHEMA_VERSION

        if raw_version < CURRENT_SCHEMA_VERSION:
            actions.append(
                lsp.CodeAction(
                    title=f"Migrate schema to v{CURRENT_SCHEMA_VERSION}",
                    kind=lsp.CodeActionKind.Source,
                    command=lsp.Command(
                        title="dlm migrate",
                        command="dlm.runInTerminal",
                        arguments=["dlm", "migrate", state.uri],
                    ),
                )
            )

    return actions


def _suggest_closest_base_model(
    state: DocumentState, diag: lsp.Diagnostic
) -> lsp.CodeAction | None:
    parsed = state.ensure_parsed()
    if parsed is None:
        return None

    current_key = parsed.frontmatter.base_model
    try:
        from dlm.base_models import BASE_MODELS

        closest = _find_closest_key(current_key, list(BASE_MODELS.keys()))
    except ImportError:
        return None

    if closest is None:
        return None

    line = diag.range.start.line
    lines = state.text.splitlines(True)
    if line >= len(lines):
        return None

    old_line = lines[line]
    stripped = old_line.lstrip()
    indent = old_line[: len(old_line) - len(stripped)]
    new_line = f"{indent}base_model: {closest}"

    return lsp.CodeAction(
        title=f"Change to '{closest}'",
        kind=lsp.CodeActionKind.QuickFix,
        diagnostics=[diag],
        edit=lsp.WorkspaceEdit(
            changes={
                state.uri: [
                    lsp.TextEdit(
                        range=lsp.Range(
                            start=lsp.Position(line=line, character=0),
                            end=lsp.Position(line=line, character=len(old_line.rstrip("\n"))),
                        ),
                        new_text=new_line,
                    )
                ]
            }
        ),
    )


def _extract_raw_dlm_version(text: str) -> int | None:
    import re

    for line in text.splitlines():
        m = re.match(r"^\s*dlm_version:\s*(\d+)", line)
        if m:
            return int(m.group(1))
    return None


def _find_closest_key(target: str, candidates: list[str]) -> str | None:
    if not candidates:
        return None
    target_lower = target.lower()
    scored = []
    for c in candidates:
        common = sum(1 for a, b in zip(target_lower, c.lower(), strict=False) if a == b)
        scored.append((common, c))
    scored.sort(key=lambda x: -x[0])
    if scored[0][0] == 0:
        return None
    return scored[0][1]
