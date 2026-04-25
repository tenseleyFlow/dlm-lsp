"""Unit tests for the per-document state cache."""

from __future__ import annotations

from dlm_lsp.doc_state import DocumentState, StateStore

_MINIMAL_DLM = """\
---
dlm_id: 01KPQ9M3000000000000000000
dlm_version: 15
base_model: smollm2-135m
---
Some prose.
"""


class TestDocumentState:
    def test_update_text_resets_cache(self) -> None:
        state = DocumentState(uri="file:///a.dlm", text=_MINIMAL_DLM)
        state.ensure_parsed()
        assert state.parsed is not None

        state.update_text("---\nbad\n---\n", 2)
        assert state.parsed is None
        assert state.diagnostics_dirty is True

    def test_ensure_parsed_caches(self) -> None:
        state = DocumentState(uri="file:///a.dlm", text=_MINIMAL_DLM)
        p1 = state.ensure_parsed()
        p2 = state.ensure_parsed()
        assert p1 is p2

    def test_ensure_parsed_records_error_on_bad_doc(self) -> None:
        state = DocumentState(uri="file:///a.dlm", text="not a dlm file")
        result = state.ensure_parsed()
        assert result is None
        assert state.parse_error is not None

    def test_ensure_parsed_empty_text_returns_none(self) -> None:
        state = DocumentState(uri="file:///a.dlm", text="   ")
        assert state.ensure_parsed() is None
        assert state.parse_error is None

    def test_ensure_base_model_spec_resolves_registry_key(self) -> None:
        state = DocumentState(uri="file:///a.dlm", text=_MINIMAL_DLM)
        spec = state.ensure_base_model_spec()
        assert spec is not None
        assert spec["key"] == "smollm2-135m"
        assert isinstance(spec["params"], int)

    def test_ensure_base_model_spec_returns_none_for_unknown(self) -> None:
        dlm = _MINIMAL_DLM.replace("smollm2-135m", "hf:unknown/model")
        state = DocumentState(uri="file:///a.dlm", text=dlm)
        spec = state.ensure_base_model_spec()
        assert spec is None


class TestStateStore:
    def test_open_get_close_lifecycle(self) -> None:
        store = StateStore()
        state = store.open("file:///a.dlm", _MINIMAL_DLM, version=1)
        assert store.get("file:///a.dlm") is state
        store.close("file:///a.dlm")
        assert store.get("file:///a.dlm") is None

    def test_update_refreshes_text(self) -> None:
        store = StateStore()
        store.open("file:///a.dlm", _MINIMAL_DLM, version=1)
        updated = store.update("file:///a.dlm", "new text", version=2)
        assert updated is not None
        assert updated.text == "new text"
        assert updated.version == 2

    def test_update_unknown_uri_returns_none(self) -> None:
        store = StateStore()
        assert store.update("file:///unknown.dlm", "text", 1) is None

    def test_close_unknown_uri_is_noop(self) -> None:
        store = StateStore()
        store.close("file:///unknown.dlm")
