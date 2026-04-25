"""Per-document parsed state cache for the LSP server."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class DocumentState:
    """Cached parse result + resolved metadata for a single .dlm document."""

    uri: str
    text: str = ""
    version: int = 0
    parsed: Any | None = None
    base_model_spec: dict[str, Any] | None = None
    parse_error: str | None = None
    diagnostics_dirty: bool = True

    def update_text(self, text: str, version: int) -> None:
        self.text = text
        self.version = version
        self.parsed = None
        self.base_model_spec = None
        self.parse_error = None
        self.diagnostics_dirty = True

    def ensure_parsed(self) -> Any | None:
        if self.parsed is not None:
            return self.parsed
        if not self.text.strip():
            return None
        try:
            from dlm.doc.parser import parse_text

            self.parsed = parse_text(self.text)
            self.parse_error = None
        except Exception as exc:
            self.parse_error = str(exc)
            self.parsed = None
            _log.debug("parse failed for %s: %s", self.uri, exc)
        return self.parsed

    def ensure_base_model_spec(self) -> dict[str, Any] | None:
        if self.base_model_spec is not None:
            return self.base_model_spec
        parsed = self.ensure_parsed()
        if parsed is None:
            return None
        try:
            from dlm.base_models import BASE_MODELS

            key = parsed.frontmatter.base_model
            spec = BASE_MODELS.get(key)
            if spec is not None:
                self.base_model_spec = {
                    "key": spec.key,
                    "hf_id": spec.hf_id,
                    "params": spec.params,
                    "size_gb_fp16": spec.size_gb_fp16,
                    "context_length": spec.context_length,
                    "modality": spec.modality,
                    "license_spdx": spec.license_spdx,
                    "requires_acceptance": spec.requires_acceptance,
                }
        except Exception as exc:
            _log.debug("base model resolution failed: %s", exc)
        return self.base_model_spec


@dataclass
class StateStore:
    """Maps document URIs to their cached state."""

    _docs: dict[str, DocumentState] = field(default_factory=dict)

    def open(self, uri: str, text: str, version: int = 0) -> DocumentState:
        state = DocumentState(uri=uri, text=text, version=version)
        self._docs[uri] = state
        return state

    def get(self, uri: str) -> DocumentState | None:
        return self._docs.get(uri)

    def close(self, uri: str) -> None:
        self._docs.pop(uri, None)

    def update(self, uri: str, text: str, version: int) -> DocumentState | None:
        state = self._docs.get(uri)
        if state is None:
            return None
        state.update_text(text, version)
        return state
