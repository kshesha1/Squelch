"""JSONL event log (spec §4.2). Append-only, one event per line."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from squelch.schemas import EVENT_TYPES, Event


class EventLog:
    def __init__(self, path: Path, run_id: str):
        self.path = Path(path)
        self.run_id = run_id
        self._sequence = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        type: str,
        payload: dict[str, Any] | None = None,
        *,
        stage_id: str | None = None,
        agent_id: str = "harness",
        phase: str = "run",
    ) -> Event:
        if type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {type}")
        self._sequence += 1
        event = Event(
            event_id=f"{self.run_id}:{self._sequence:04d}",
            run_id=self.run_id,
            stage_id=stage_id,
            sequence=self._sequence,
            agent_id=agent_id,
            phase=phase,
            type=type,
            payload=payload or {},
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n")
        return event
