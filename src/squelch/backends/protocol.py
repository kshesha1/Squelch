"""Backend protocol: a minimal, explicit tool-calling interface.

The runner talks to any model backend through this shape. The scripted
backend implements it deterministically for free harness tests; the
Anthropic backend (ticket P1.4) will implement it over the official SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from squelch.schemas import TokenUsage


class BackendError(RuntimeError):
    """Provider/infrastructure failure — maps to run status `invalid`."""


@dataclass(frozen=True)
class ToolCall:
    tool_call_id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    output: str
    is_error: bool = False


@dataclass
class ModelRequest:
    system: str
    messages: list[dict[str, Any]]  # neutral transcript: role/content/tool results
    tools: list[dict[str, Any]]
    max_output_tokens: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    text: str | None
    tool_calls: list[ToolCall]
    usage: TokenUsage
    reported_model_id: str | None = None
    stop_reason: str | None = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class ModelBackend(Protocol):
    name: str

    def complete(self, request: ModelRequest) -> ModelResponse: ...
