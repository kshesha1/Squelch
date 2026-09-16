"""Ollama backend: local LLM inference, no API key, no cloud spend.

Talks to a local Ollama server (default http://localhost:11434) via the
documented ``POST /api/chat`` endpoint with function tools. Verified
against the official API documentation (docs/api.md, retrieved
2026-09-16):

- tools: ``{"type": "function", "function": {name, description, parameters}}``
- assistant tool calls: ``message.tool_calls[].function.{name, arguments}``
- tool results: ``{"role": "tool", "content": ..., "tool_name": ...}``
- token counts: ``prompt_eval_count`` / ``eval_count``
- determinism aids: ``options.seed`` / ``options.temperature`` (local
  sampling seeds improve repeatability but are NOT a determinism claim)

Ollama's documented tool_calls carry no call ID, so this backend
synthesizes deterministic per-conversation IDs.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from squelch.backends.protocol import BackendError, ModelRequest, ModelResponse, ToolCall
from squelch.schemas import TokenUsage

DEFAULT_HOST = "http://localhost:11434"


def _to_ollama_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


def _to_ollama_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        role = m["role"]
        if role == "user":
            out.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.get("content") or ""}
            if m.get("tool_calls"):
                entry["tool_calls"] = [
                    {"function": {"name": c["name"], "arguments": c["input"]}}
                    for c in m["tool_calls"]
                ]
            out.append(entry)
        elif role == "tool":
            for r in m["content"]:
                out.append(
                    {
                        "role": "tool",
                        "content": r["output"],
                        "tool_name": r.get("name", ""),
                    }
                )
        else:
            raise BackendError(f"unknown message role for ollama backend: {role!r}")
    return out


class OllamaBackend:
    name = "ollama"

    def __init__(
        self,
        model: str,
        *,
        host: str = DEFAULT_HOST,
        temperature: float = 0.0,
        seed: int | None = None,
        request_timeout_seconds: int = 600,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.seed = seed
        self.request_timeout_seconds = request_timeout_seconds
        self._call_counter = 0

    # -- transport (separated for testability) -------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{self.host}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:2000]
            raise BackendError(f"ollama HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BackendError(
                f"ollama unreachable or invalid response at {self.host}: {exc}"
            ) from exc

    def server_version(self) -> str:
        """Reachability probe used by `doctor` and pre-campaign smoke checks."""
        req = urllib.request.Request(f"{self.host}/api/version")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8")).get("version", "unknown")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BackendError(f"ollama server not reachable at {self.host}: {exc}") from exc

    # -- protocol ------------------------------------------------------------

    def complete(self, request: ModelRequest) -> ModelResponse:
        options: dict[str, Any] = {
            "temperature": self.temperature,
            "num_predict": request.max_output_tokens,
        }
        if self.seed is not None:
            options["seed"] = self.seed
        payload = {
            "model": self.model,
            "messages": _to_ollama_messages(request.system, request.messages),
            "tools": _to_ollama_tools(request.tools),
            "stream": False,
            "options": options,
        }
        data = self._post("/api/chat", payload)

        message = data.get("message")
        if not isinstance(message, dict):
            raise BackendError(f"ollama response missing message: {list(data)}")

        calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            fn = raw.get("function") or {}
            name = fn.get("name")
            if not name:
                raise BackendError(f"ollama tool_call missing function name: {raw}")
            args = fn.get("arguments")
            if isinstance(args, str):  # some models emit stringified JSON
                try:
                    args = json.loads(args)
                except json.JSONDecodeError as exc:
                    raise BackendError(
                        f"ollama tool_call arguments not parseable: {args[:500]}"
                    ) from exc
            if not isinstance(args, dict):
                args = {}
            self._call_counter += 1
            calls.append(
                ToolCall(
                    tool_call_id=f"ollama-{self._call_counter:04d}",
                    name=name,
                    input=args,
                )
            )

        usage = TokenUsage(
            input_tokens=int(data.get("prompt_eval_count") or 0),
            output_tokens=int(data.get("eval_count") or 0),
        )
        return ModelResponse(
            text=message.get("content") or None,
            tool_calls=calls,
            usage=usage,
            reported_model_id=data.get("model"),
            stop_reason=data.get("done_reason"),
        )
