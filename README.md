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
