"""textDocument/completion handler for .dlm files."""

from __future__ import annotations

import re
from typing import Any

from lsprotocol import types as lsp

from dlm_lsp.doc_state import DocumentState

_FRONTMATTER_DELIM = re.compile(r"^---\s*$")


def compute_completions(
    state: DocumentState, position: lsp.Position
) -> lsp.CompletionList | None:
    lines = state.text.splitlines()
    if position.line >= len(lines):
        return None

    line_text = lines[position.line]
    in_frontmatter = _cursor_in_frontmatter(lines, position.line)

    if in_frontmatter:
        return _frontmatter_completions(lines, position, line_text)
    return _body_completions(line_text, position)


def _cursor_in_frontmatter(lines: list[str], cursor_line: int) -> bool:
    delim_count = 0
    for i, line in enumerate(lines):
        if i > cursor_line:
            break
        if _FRONTMATTER_DELIM.match(line):
            delim_count += 1
    return delim_count == 1


def _frontmatter_completions(
    lines: list[str], position: lsp.Position, line_text: str
) -> lsp.CompletionList | None:
    stripped = line_text.strip()

    if stripped.startswith("base_model:") or re.match(r"^base_model:\s*", stripped):
        return _base_model_completions()

    if stripped.startswith("adapter:") or re.match(r"^adapter:\s*", stripped):
        return _adapter_type_completions()

    if stripped.startswith("default_quant:") or re.match(r"^default_quant:\s*", stripped):
        return _quant_completions()

    if _is_empty_or_key_position(stripped):
        return _top_level_key_completions()

    return None


def _body_completions(
    line_text: str, position: lsp.Position
) -> lsp.CompletionList | None:
    stripped = line_text.strip()
    if stripped.startswith("::") or stripped == "":
        return _section_fence_completions()
    return None


def _base_model_completions() -> lsp.CompletionList:
    items: list[lsp.CompletionItem] = []
    try:
        from dlm.base_models import BASE_MODELS

        for key, spec in sorted(BASE_MODELS.items()):
            params_label = _format_params(spec.params)
            detail = f"{params_label} | {spec.size_gb_fp16:.1f} GB | ctx {spec.context_length}"
            if spec.modality != "text":
                detail += f" | {spec.modality}"
            items.append(
                lsp.CompletionItem(
                    label=key,
                    kind=lsp.CompletionItemKind.Value,
                    detail=detail,
                    documentation=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown,
                        value=(
                            f"**{key}**\n\n"
                            f"- HF: `{spec.hf_id}`\n"
                            f"- Parameters: {params_label}\n"
                            f"- Context: {spec.context_length}\n"
                            f"- License: {spec.license_spdx}\n"
                        ),
                    ),
                    insert_text=key,
                )
            )
    except ImportError:
        pass
    return lsp.CompletionList(is_incomplete=False, items=items)


def _adapter_type_completions() -> lsp.CompletionList:
    items = [
        lsp.CompletionItem(
            label="lora",
            kind=lsp.CompletionItemKind.Value,
            detail="Low-Rank Adaptation (default)",
        ),
        lsp.CompletionItem(
            label="qlora",
            kind=lsp.CompletionItemKind.Value,
            detail="4-bit quantized LoRA (requires CUDA SM >= 8.0)",
        ),
        lsp.CompletionItem(
            label="dora",
            kind=lsp.CompletionItemKind.Value,
            detail="Weight-decomposed LoRA",
        ),
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


def _quant_completions() -> lsp.CompletionList:
    quants = ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"]
    items = [
        lsp.CompletionItem(label=q, kind=lsp.CompletionItemKind.Value)
        for q in quants
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


def _section_fence_completions() -> lsp.CompletionList:
    items = [
        lsp.CompletionItem(
            label="::instruction::",
            kind=lsp.CompletionItemKind.Snippet,
            detail="Supervised fine-tuning Q&A section",
            insert_text="::instruction::\n### Q\n$1\n\n### A\n$2\n",
            insert_text_format=lsp.InsertTextFormat.Snippet,
        ),
        lsp.CompletionItem(
            label="::preference::",
            kind=lsp.CompletionItemKind.Snippet,
            detail="DPO/ORPO preference section",
            insert_text="::preference::\n### Prompt\n$1\n\n### Chosen\n$2\n\n### Rejected\n$3\n",
            insert_text_format=lsp.InsertTextFormat.Snippet,
        ),
        lsp.CompletionItem(
            label="::image::",
            kind=lsp.CompletionItemKind.Snippet,
            detail="Vision-language image section",
            insert_text='::image path="$1" alt="$2"::\n$3\n',
            insert_text_format=lsp.InsertTextFormat.Snippet,
        ),
        lsp.CompletionItem(
            label="::audio::",
            kind=lsp.CompletionItemKind.Snippet,
            detail="Audio-language section",
            insert_text='::audio path="$1" transcript="$2"::\n$3\n',
            insert_text_format=lsp.InsertTextFormat.Snippet,
        ),
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


def _top_level_key_completions() -> lsp.CompletionList:
    keys = [
        ("base_model", "Base model registry key or hf:org/name"),
        ("system_prompt", "System message prepended to training examples"),
        ("training", "Training configuration block"),
        ("export", "Export configuration block"),
    ]
    items = [
        lsp.CompletionItem(
            label=f"{k}:",
            kind=lsp.CompletionItemKind.Property,
            detail=desc,
        )
        for k, desc in keys
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


def _is_empty_or_key_position(stripped: str) -> bool:
    return stripped == "" or (not stripped.startswith("#") and ":" not in stripped)


def _format_params(params: int) -> str:
    if params >= 1_000_000_000:
        return f"{params / 1_000_000_000:.1f}B"
    if params >= 1_000_000:
        return f"{params / 1_000_000:.0f}M"
    return f"{params / 1_000:.0f}K"
