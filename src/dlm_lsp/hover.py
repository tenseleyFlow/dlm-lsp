"""textDocument/hover handler for .dlm files."""

from __future__ import annotations

import re

from lsprotocol import types as lsp

from dlm_lsp.completions import _cursor_in_frontmatter, _format_params
from dlm_lsp.doc_state import DocumentState

_FENCE_RE = re.compile(r"^::(instruction|preference|image|audio|prose)(?:#\w+)?(?:\s.*)?::$")
_BASE_MODEL_RE = re.compile(r"^base_model:\s*(.+)$")


def compute_hover(state: DocumentState, position: lsp.Position) -> lsp.Hover | None:
    lines = state.text.splitlines()
    if position.line >= len(lines):
        return None

    line_text = lines[position.line]
    in_frontmatter = _cursor_in_frontmatter(lines, position.line)

    if in_frontmatter:
        return _frontmatter_hover(state, line_text, position)
    return _body_hover(line_text, position)


def _frontmatter_hover(
    state: DocumentState, line_text: str, position: lsp.Position
) -> lsp.Hover | None:
    m = _BASE_MODEL_RE.match(line_text.strip())
    if m:
        return _base_model_hover(state, m.group(1).strip(), position)
    return None


def _body_hover(line_text: str, position: lsp.Position) -> lsp.Hover | None:
    m = _FENCE_RE.match(line_text.strip())
    if m:
        section_type = m.group(1)
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.Markdown,
                value=f"**Section fence:** `{section_type}`",
            ),
            range=lsp.Range(
                start=lsp.Position(line=position.line, character=0),
                end=lsp.Position(line=position.line, character=len(line_text)),
            ),
        )
    return None


def _base_model_hover(
    state: DocumentState, key: str, position: lsp.Position
) -> lsp.Hover | None:
    spec = state.ensure_base_model_spec()
    if spec is None:
        try:
            from dlm.base_models import BASE_MODELS

            raw_spec = BASE_MODELS.get(key)
            if raw_spec is None:
                return lsp.Hover(
                    contents=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown,
                        value=f"**Unknown base model:** `{key}`\n\nNot found in the registry.",
                    ),
                )
            spec = {
                "key": raw_spec.key,
                "hf_id": raw_spec.hf_id,
                "params": raw_spec.params,
                "size_gb_fp16": raw_spec.size_gb_fp16,
                "context_length": raw_spec.context_length,
                "modality": raw_spec.modality,
                "license_spdx": raw_spec.license_spdx,
                "requires_acceptance": raw_spec.requires_acceptance,
            }
        except ImportError:
            return None

    params_label = _format_params(spec["params"])
    acceptance = " (gated)" if spec.get("requires_acceptance") else ""
    md = (
        f"### {spec['key']}\n\n"
        f"| Property | Value |\n"
        f"|----------|-------|\n"
        f"| HF ID | `{spec['hf_id']}` |\n"
        f"| Parameters | {params_label} |\n"
        f"| FP16 Size | {spec['size_gb_fp16']:.1f} GB |\n"
        f"| Context | {spec['context_length']} tokens |\n"
        f"| Modality | {spec['modality']} |\n"
        f"| License | {spec['license_spdx']}{acceptance} |\n"
    )
    return lsp.Hover(
        contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=md),
    )
