"""Offline re-analysis must re-derive labels without inventing runs."""

import json

import pytest

from squelch.analysis.replay import (
    ReplayError,
    check_replay_validity,
    derive_termination,
    reclassify,
)
from squelch.schemas import (
    AssertionOutcome,
    RunResult,
    RunStatus,
    StageResult,
    TerminationReason,
    TokenUsage,
)


def ev(seq, type_, payload):
    return {"event_id": f"r:{seq:04d}", "run_id": "r", "stage_id": "implement",
            "sequence": seq, "agent_id": "worker-1", "phase": "run",
            "type": type_, "payload": payload}


def make_result(status=RunStatus.COMPLETED, success=True, mandatory_pass=True):
    return RunResult(
        run_id="r",
        status=status,
        task_success=success,
        assertions=[AssertionOutcome(assertion_id="a", passed=mandatory_pass,
                                     mandatory=True)],
        usage=TokenUsage(input_tokens=10, output_tokens=2048),
        termination_reason=TerminationReason.FINAL_RESPONSE,
        stage_results=[StageResult(
            stage_id="implement", worker_id="worker-1", exposed_skill_ids=[],
            model_calls=2, tool_calls=1, usage=TokenUsage(),
            handoff_produced=False,
            termination_reason=TerminationReason.FINAL_RESPONSE)],
    )


def test_truncated_response_reclassified_to_agent_limit():
    events = [
        ev(1, "run_started", {}),
        ev(2, "model_response", {"stop_reason": "stop", "tool_call_count": 1}),
        ev(3, "model_response", {"stop_reason": "length", "tool_call_count": 0}),
    ]
    out = reclassify(make_result(), events)
    assert out.status is RunStatus.AGENT_LIMIT
    assert out.termination_reason is TerminationReason.OUTPUT_TOKEN_LIMIT
    assert out.task_success is False
    assert out.stage_results[-1].termination_reason is TerminationReason.OUTPUT_TOKEN_LIMIT


def test_clean_run_is_unchanged():
    events = [
        ev(1, "run_started", {}),
        ev(2, "model_response", {"stop_reason": "stop", "tool_call_count": 0}),
    ]
    out = reclassify(make_result(), events)
    assert out.status is RunStatus.COMPLETED
    assert out.termination_reason is TerminationReason.FINAL_RESPONSE
    assert out.task_success is True


def test_grading_is_never_rewritten():
    """A failing task stays failing; replay re-derives status, not correctness."""
    events = [ev(1, "model_response", {"stop_reason": "stop", "tool_call_count": 0})]
    out = reclassify(make_result(mandatory_pass=False), events)
    assert out.status is RunStatus.COMPLETED
    assert out.task_success is False
    assert out.assertions[0].passed is False


def test_truncation_with_tool_calls_is_refused():
    """The corrected runner would have stopped instead of running those tools.

    The rest of that run never happened, so it cannot be re-derived — replay
    must refuse rather than fabricate it.
    """
    events = [
        ev(1, "model_response", {"stop_reason": "length", "tool_call_count": 2}),
        ev(2, "tool_completed", {"name": "write_file"}),
    ]
    validity = check_replay_validity(events)
    assert not validity.ok
    assert "never happened" in validity.reasons[0]
    with pytest.raises(ReplayError, match="never happened"):
        reclassify(make_result(), events)


@pytest.mark.parametrize("limit,expected", [
    ("max_model_calls", TerminationReason.MODEL_CALL_LIMIT),
    ("max_tool_calls", TerminationReason.TOOL_CALL_LIMIT),
    ("task_timeout_seconds", TerminationReason.TIMEOUT),
    ("max_output_tokens", TerminationReason.OUTPUT_TOKEN_LIMIT),
])
def test_limit_events_map_to_reasons(limit, expected):
    assert derive_termination([ev(1, "limit_reached", {"limit": limit})]) is expected


def test_backend_error_becomes_invalid():
    events = [ev(1, "run_error", {"kind": "backend", "error": "outage"})]
    out = reclassify(make_result(), events)
    assert out.status is RunStatus.INVALID
    assert out.task_success is None


def test_replay_study_writes_derived_study_and_leaves_source_intact(tmp_path):
    from squelch.analysis.replay import replay_study

    source = tmp_path / "src"
    (source / "runs" / "r1").mkdir(parents=True)
    (source / "study.json").write_text(json.dumps({
        "schema_version": "1", "campaign": "orig", "cells": [], "status_counts": {},
        "disclosure": "base.",
    }))
    result = make_result()
    (source / "runs" / "r1" / "result.json").write_text(
        json.dumps(result.model_dump(mode="json")))
    (source / "runs" / "r1" / "run_spec.json").write_text(json.dumps({
        "run_id": "r", "condition_id": "ab", "task": {"task_id": "t1"},
    }))
    (source / "runs" / "r1" / "events.jsonl").write_text(
        json.dumps(ev(1, "model_response", {"stop_reason": "length",
                                            "tool_call_count": 0})) + "\n")
    before = (source / "runs" / "r1" / "result.json").read_text()

    summary = replay_study(source, tmp_path / "derived")

    assert (source / "runs" / "r1" / "result.json").read_text() == before  # immutable
    assert summary["analysis_version"] == "replay/1"
    assert summary["derived_from"] == "orig"
    assert len(summary["reclassified_runs"]) == 1
    assert summary["status_counts"] == {"agent_limit": 1}
    assert "No model was called" in summary["disclosure"]
    assert summary["condition_diagnostics"][0]["truncated_runs"] == 1


def test_replay_refuses_to_overwrite_existing_derived_study(tmp_path):
    from squelch.analysis.replay import replay_study

    source = tmp_path / "src"
    (source / "runs").mkdir(parents=True)
    (source / "study.json").write_text(json.dumps(
        {"schema_version": "1", "campaign": "o", "cells": [], "status_counts": {}}))
    dest = tmp_path / "dest"
    dest.mkdir()
    with pytest.raises(ReplayError, match="already exists"):
        replay_study(source, dest)
