"""Ollama backend tests with a mocked transport — no server required."""

import pytest

from squelch.backends.ollama import OllamaBackend, _to_ollama_messages, _to_ollama_tools
from squelch.backends.protocol import BackendError, ModelRequest
from squelch.runner.tools import TOOL_SCHEMAS


def make_request(messages=None):
    return ModelRequest(
        system="be helpful",
        messages=messages or [{"role": "user", "content": "do the task"}],
        tools=TOOL_SCHEMAS,
        max_output_tokens=512,
    )


class MockedBackend(OllamaBackend):
    def __init__(self, responses, **kwargs):
        super().__init__("test-model:1b", **kwargs)
        self._responses = list(responses)
        self.requests = []

    def _post(self, path, payload):
        self.requests.append((path, payload))
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def chat_response(content="", tool_calls=None, done_reason="stop"):
    msg = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {"model": "test-model:1b", "message": msg, "done": True,
            "done_reason": done_reason, "prompt_eval_count": 120, "eval_count": 45}


def test_tool_definitions_wrapped_in_function_format():
    backend = MockedBackend([chat_response("hi")])
    backend.complete(make_request())
    _, payload = backend.requests[0]
    tool = payload["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "list_files"
    assert "parameters" in tool["function"]
    assert payload["stream"] is False
    assert payload["options"]["num_predict"] == 512


def test_system_prompt_becomes_system_message():
    backend = MockedBackend([chat_response("hi")])
    backend.complete(make_request())
    _, payload = backend.requests[0]
    assert payload["messages"][0] == {"role": "system", "content": "be helpful"}


def test_tool_calls_parsed_with_synthetic_ids():
    backend = MockedBackend([
        chat_response(tool_calls=[
            {"function": {"name": "write_file",
                          "arguments": {"path": "a.txt", "content": "x"}}},
            {"function": {"name": "list_files", "arguments": {}}},
        ])
    ])
    resp = backend.complete(make_request())
    assert [c.name for c in resp.tool_calls] == ["write_file", "list_files"]
    assert resp.tool_calls[0].input == {"path": "a.txt", "content": "x"}
    ids = [c.tool_call_id for c in resp.tool_calls]
    assert len(set(ids)) == 2


def test_stringified_arguments_parsed():
    backend = MockedBackend([
        chat_response(tool_calls=[
            {"function": {"name": "read_file", "arguments": '{"path": "f.txt"}'}},
        ])
    ])
    resp = backend.complete(make_request())
    assert resp.tool_calls[0].input == {"path": "f.txt"}


def test_usage_mapped_from_eval_counts():
    backend = MockedBackend([chat_response("done")])
    resp = backend.complete(make_request())
    assert resp.usage.input_tokens == 120
    assert resp.usage.output_tokens == 45
    assert resp.reported_model_id == "test-model:1b"


def test_tool_results_become_tool_role_messages():
    messages = [
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "x1", "name": "read_file", "input": {"path": "f"}}]},
        {"role": "tool", "content": [
            {"tool_call_id": "x1", "name": "read_file", "output": "contents",
             "is_error": False},
        ]},
    ]
    out = _to_ollama_messages("sys", messages)
    assert out[-1] == {"role": "tool", "content": "contents", "tool_name": "read_file"}
    assistant = out[-2]
    assert assistant["tool_calls"][0]["function"]["name"] == "read_file"
    assert assistant["tool_calls"][0]["function"]["arguments"] == {"path": "f"}


def test_transport_error_is_backend_error():
    backend = MockedBackend([TimeoutError("slow")])
    with pytest.raises((BackendError, TimeoutError)):
        # _post is mocked to raise directly; real transport wraps into
        # BackendError — this asserts complete() does not swallow errors
        backend.complete(make_request())


def test_missing_message_is_backend_error():
    backend = MockedBackend([{"done": True}])
    with pytest.raises(BackendError, match="missing message"):
        backend.complete(make_request())


def test_tool_schema_conversion_covers_all_tools():
    converted = _to_ollama_tools(TOOL_SCHEMAS)
    assert {t["function"]["name"] for t in converted} == {
        "list_files", "read_file", "write_file", "run_checks"
    }
