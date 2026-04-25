"""Unit tests for the training progress notification."""

from __future__ import annotations

from typing import Any

from dlm_lsp.progress import TrainingProgress, notify_training_progress


class TestTrainingProgress:
    def test_to_dict_excludes_none_fields(self) -> None:
        p = TrainingProgress(run_id=1, step=10, total_steps=100, loss=0.5)
        d = p.to_dict()
        assert d == {
            "run_id": 1,
            "step": 10,
            "total_steps": 100,
            "loss": 0.5,
            "phase": "sft",
        }
        assert "adapter_name" not in d

    def test_to_dict_includes_all_when_set(self) -> None:
        p = TrainingProgress(
            run_id=2,
            step=5,
            total_steps=50,
            loss=1.2,
            phase="preference",
            adapter_name="tone",
        )
        d = p.to_dict()
        assert d["adapter_name"] == "tone"
        assert d["phase"] == "preference"


class TestNotifyTrainingProgress:
    def test_sends_notification(self) -> None:
        sent: list[tuple[str, Any]] = []

        class _Server:
            def send_notification(self, method: str, params: Any) -> None:
                sent.append((method, params))

        server = _Server()
        progress = TrainingProgress(run_id=1, step=3, total_steps=10, loss=0.8)
        notify_training_progress(server, progress)
        assert len(sent) == 1
        assert sent[0][0] == "dlm/trainingProgress"
        assert sent[0][1]["step"] == 3

    def test_swallows_send_errors(self) -> None:
        class _BrokenServer:
            def send_notification(self, method: str, params: Any) -> None:
                raise ConnectionError("disconnected")

        progress = TrainingProgress(run_id=1, step=1, total_steps=10)
        notify_training_progress(_BrokenServer(), progress)
