"""Scripted backend: deterministic, free, offline.

A transcript is a JSON file:

```json
{
  "schema_version": "1",
  "steps": [
    {"tool_calls": [{"name": "write_file", "input": {"path": "config.json", "content": "{}"}}]},
    {"final": "Done."}
  ]
}
```

Each `complete()` call consumes one step. Steps either issue tool calls or
end the loop with a final text. Runs driven by this backend carry
``evidence_stage: scripted`` — they validate the program, never a
model-performance claim (spec §4.1).

A transcript may also declare ``{"error": "..."}`` as a step to simulate a
provider failure, exercising the `invalid` status path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from squelch.backends.protocol import BackendError, ModelRequest, ModelResponse, ToolCall
from squelch.schemas import TokenUsage


def load_transcript(path: Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != "1":
        raise ValueError(f"unsupported transcript schema_version in {path}")
    steps = data["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"transcript {path} has no steps")
    return steps


class ScriptedBackend:
    """Replays a fixed list of steps, ignoring message content."""

    name = "scripted"

    def __init__(self, steps: list[dict[str, Any]]):
        self._steps = list(steps)
        self._cursor = 0
        self._call_counter = 0

    @classmethod
    def from_file(cls, path: Path) -> ScriptedBackend:
        return cls(load_transcript(path))

    def complete(self, request: ModelRequest) -> ModelResponse:
        if self._cursor >= len(self._steps):
            raise BackendError("scripted transcript exhausted: runner requested another step")
        step = self._steps[self._cursor]
        self._cursor += 1

        if "error" in step:
            raise BackendError(f"scripted provider error: {step['error']}")

        usage = TokenUsage(
            input_tokens=int(step.get("input_tokens", 100)),
            output_tokens=int(step.get("output_tokens", 50)),
        )
        if "tool_calls" in step:
            calls = []
            for raw in step["tool_calls"]:
                self._call_counter += 1
                calls.append(
                    ToolCall(
                        tool_call_id=f"scripted-{self._call_counter:04d}",
                        name=raw["name"],
                        input=dict(raw.get("input", {})),
                    )
                )
            return ModelResponse(
                text=step.get("text"),
                tool_calls=calls,
                usage=usage,
                reported_model_id="scripted",
                stop_reason="tool_use",
            )
        if "final" in step:
            return ModelResponse(
                text=str(step["final"]),
                tool_calls=[],
                usage=usage,
                reported_model_id="scripted",
                stop_reason="end_turn",
            )
        raise ValueError(f"scripted step must contain tool_calls, final, or error: {step}")
