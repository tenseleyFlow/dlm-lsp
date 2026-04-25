"""LSP capability constants and version metadata."""

from __future__ import annotations

from typing import Final

SERVER_NAME: Final[str] = "dlm-lsp"
SERVER_VERSION: Final[str] = "0.1.0"

COMPLETION_TRIGGER_CHARACTERS: Final[list[str]] = [":", ".", "-", " "]
