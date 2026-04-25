"""dlm/trainingProgress custom notification bridge.

The trainer emits progress events when invoked with ``--lsp-notify``.
This module defines the notification type and a helper to broadcast
it to connected clients.
"""

from __future__ import annotations

import contextlib
from dataclasses import asdict, dataclass
from typing import Any

TRAINING_PROGRESS_METHOD = "dlm/trainingProgress"


@dataclass(frozen=True)
class TrainingProgress:
    """Payload for the ``dlm/trainingProgress`` custom notification."""

    run_id: int
    step: int
    total_steps: int
    loss: float | None = None
    phase: str = "sft"
    adapter_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def notify_training_progress(
    server: Any,
    progress: TrainingProgress,
) -> None:
    """Push a training progress notification to the connected client."""
    with contextlib.suppress(Exception):
        server.send_notification(TRAINING_PROGRESS_METHOD, progress.to_dict())
