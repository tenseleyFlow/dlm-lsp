# dlm-lsp

Language Server Protocol backend for `.dlm` files.

## Features

- **Completions** — base model registry keys, frontmatter fields, section fences with snippets
- **Hover** — base model specs (params, size, context, license), section fence info
- **Diagnostics** — schema validation errors, unknown base models, frontmatter structure
- **Code Actions** — schema migration, base model fixes

## Install

```bash
pip install dlm-lsp
```

This pulls `document-language-model` from PyPI as a runtime dependency.

## Compatibility

| `dlm-lsp` | `document-language-model` |
| :-- | :-- |
| `0.1.x` | `0.10.x` |

The LSP imports from `dlm.doc.parser`, `dlm.doc.schema`, `dlm.base_models`,
and `dlm.store.manifest`. A major-version drift on either side can break
imports or schema validation. The LSP logs both versions at startup
(visible in your editor's LSP log channel) so mismatches surface
immediately. Pin a matching pair if you mix custom forks.

## Usage

The `dlm-lsp` binary launches a Language Server over stdio:

```bash
dlm-lsp
```

VSCode, Neovim, Helix, and Zed can connect to it as an LSP server for `.dlm` files.

## Development

```bash
uv sync --dev
uv run pytest tests/
uv run mypy src/dlm_lsp
uv run ruff check .
```
