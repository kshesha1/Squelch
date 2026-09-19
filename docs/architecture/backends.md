---
title: Backends
---

# Backends

A backend is anything that can answer one step of the agent loop. The runner sees only this interface (`backends/protocol.py`):

```python
class ModelBackend(Protocol):
    name: str
    def complete(self, request: ModelRequest) -> ModelResponse: ...
```

A `ModelRequest` carries the system prompt, the conversation so far, the tool schemas, and the output-token cap. A `ModelResponse` carries optional text, zero or more tool calls, token usage, the model's *reported* id, and a stop reason.

Because the runner depends only on this protocol, swapping the puppet for a real model changes nothing else.

A backend that fails raises `BackendError`, which ends the run as `invalid`.

## `scripted`: the deterministic puppet

Replays a JSON transcript, one step per `complete()` call:

```json
{
  "schema_version": "1",
  "steps": [
    {"tool_calls": [{"name": "read_file", "input": {"path": "ranges.py"}}]},
    {"tool_calls": [{"name": "write_file",
                     "input": {"path": "ranges.py", "content": "..."}}]},
    {"final": "Fixed the boundary."}
  ]
}
```

- A step is either `tool_calls`, a `final` message, or an `error` (which simulates a provider failure to test the `invalid` path).
- Usage defaults to 100 input / 50 output tokens per step unless overridden.
- Running past the end of a transcript raises `BackendError`.
- The campaign locates a transcript at `<scripted_transcripts>/<task_id>/<condition_id>.json`.

Free, repeatable, and used to test the harness itself. Scripted results are always labelled `scripted` evidence.

## `ollama`: real local inference

`backends/ollama.py` talks to a local Ollama server through the documented `POST /api/chat` endpoint. The tool-use format was checked against Ollama's API documentation before implementation.

| Squelch concept | Ollama API |
|---|---|
| Tool definitions | `tools: [{"type":"function","function":{name, description, parameters}}]` |
| System prompt | a leading `{"role":"system"}` message |
| Assistant tool calls | `message.tool_calls[].function.{name, arguments}` |
| Tool results | `{"role":"tool","content":...,"tool_name":...}` |
| Token usage | `prompt_eval_count` / `eval_count` |
| Stop reason | `done_reason` |
| Determinism aids | `options.temperature`, `options.seed` |
| Output cap | `options.num_predict` |

Details worth knowing:

- Requests are sent with `stream: false`.
- Ollama's tool calls carry no id, so the backend synthesises stable ones (`ollama-0001`, ...).
- `arguments` may arrive as an object or as a JSON string; both are handled.
- Transport errors, HTTP errors, and unparseable responses all become `BackendError`.
- `server_version()` probes `/api/version`; it's used by `doctor` and as a smoke check before any live campaign.
- The default request timeout is 600 seconds.
- A fixed sampling seed improves repeatability but is **not** a determinism claim about a hosted or local model.

The Ollama backend is tested with a mocked transport ([`test_ollama_backend.py`](https://github.com/kshesha1/Squelch/blob/main/tests/unit/test_ollama_backend.py)), so no server is needed in CI.

## Adding another backend

Implement `complete()` and register it in `_make_backend()` and the `SUPPORTED_BACKENDS` set in `experiments/campaign.py`. Two things to get right:

1. **Map stop reasons** so a cut-off response reports `length` or `max_tokens`. That is how truncation is detected.
2. **Report cost honestly.** A provider without a price table stays `cost_unknown`; only local inference records a known zero cost. This is pinned by a test.

Hosted-API backends are not implemented.
