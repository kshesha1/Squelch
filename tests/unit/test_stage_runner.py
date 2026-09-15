import json

import pytest

from squelch.backends.scripted import ScriptedBackend
from squelch.runner.stage import (
    MAX_SYSTEM_PROMPT_CHARS,
    PromptEnvelopeError,
    assemble_system_prompt,
    execute_run,
)
from squelch.sandbox.envs import LocalEnv
from squelch.sandbox.evaluator import TrustedEvaluator
from squelch.schemas import (
    CollectionSnapshot,
    CompositionPolicy,
    LoadingMode,
    ModelSpec,
    ResourceLimits,
    RunSpec,
    RunStatus,
    StageSpec,
    TaskSpec,
    TaskSplit,
    TerminationReason,
)
from squelch.skills.loader import load_skill_package

PASSING_GRADER = """
import json, sys
from pathlib import Path
sub = Path(sys.argv[1])
content = (sub / "out.txt").read_text() if (sub / "out.txt").exists() else ""
print(json.dumps({"assertions": [{"id": "correct", "passed": content == "correct"}]}))
"""


@pytest.fixture
def lab(tmp_path):
    """A tiny complete lab: task, grader, starter, one skill."""
    graders = tmp_path / "graders" / "t1"
    graders.mkdir(parents=True)
    (graders / "grade.py").write_text(PASSING_GRADER)

    starter = tmp_path / "starter"
    starter.mkdir()
    (starter / "input.txt").write_text("seed")

    skill_root = tmp_path / "skills" / "tidy"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        "---\nname: tidy\ndescription: Be tidy.\n---\nAlways be tidy.\n"
    )
    skills = {"tidy": load_skill_package(skill_root)}

    task = TaskSpec(
        task_id="t1",
        family_id="fam",
        split=TaskSplit.DEVELOPMENT,
        prompt_hash="sha256:0",
        starter_tree_hash="sha256:0",
        environment_image="local:test",
        grader_hash="sha256:0",
        allowed_outputs=["out.txt"],
    )
    return {
        "task": task,
        "starter": starter,
        "skills": skills,
        "evaluator": TrustedEvaluator(LocalEnv(), tmp_path / "graders"),
        "root": tmp_path,
    }


def make_spec(task, stage_plan, run_id="run-1"):
    return RunSpec(
        run_id=run_id,
        study_id="study-1",
        condition_id="test",
        task=task,
        collection=CollectionSnapshot(
            ordered_skill_hashes=[],
            composition_policy=CompositionPolicy.SHARED,
            policy_hash="sha256:0",
            loading_mode=LoadingMode.FORCED,
            system_prompt_hash="sha256:0",
            tool_schema_hash="sha256:0",
            runner_version="test",
        ),
        model=ModelSpec(provider="scripted", requested_model_id="scripted"),
        repetition=1,
        schedule_seed=1,
        stage_plan=stage_plan,
    )


def run(lab, backend, stage_plan, run_id="run-1"):
    spec = make_spec(lab["task"], stage_plan, run_id)
    return execute_run(
        spec,
        backend=backend,
        env=LocalEnv(),
        skills=lab["skills"],
        task_prompt="Write out.txt containing exactly 'correct'.",
        starter_dir=lab["starter"],
        evaluator=lab["evaluator"],
        run_dir=lab["root"] / "runs" / run_id,
    )


ONE_STAGE = [StageSpec(stage_id="implement", exposed_skill_ids=["tidy"])]


def test_single_stage_success(lab):
    backend = ScriptedBackend([
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "out.txt", "content": "correct"}}]},
        {"final": "done"},
    ])
    result = run(lab, backend, ONE_STAGE)
    assert result.status is RunStatus.COMPLETED
    assert result.task_success is True
    assert result.termination_reason is TerminationReason.FINAL_RESPONSE
    assert len(result.stage_results) == 1
    assert result.stage_results[0].exposed_skill_ids == ["tidy"]


def test_completed_but_failing_task(lab):
    backend = ScriptedBackend([
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "out.txt", "content": "wrong"}}]},
        {"final": "done"},
    ])
    result = run(lab, backend, ONE_STAGE)
    assert result.status is RunStatus.COMPLETED
    assert result.task_success is False  # status separate from quality (§4.3)


def test_model_call_limit(lab):
    steps = [{"tool_calls": [{"name": "list_files", "input": {}}]}] * 10
    backend = ScriptedBackend(steps)
    plan = [StageSpec(stage_id="implement", exposed_skill_ids=[],
                      limits=ResourceLimits(max_model_calls=3))]
    result = run(lab, backend, plan)
    assert result.status is RunStatus.AGENT_LIMIT
    assert result.task_success is False
    assert result.termination_reason is TerminationReason.MODEL_CALL_LIMIT
    assert result.stage_results[0].model_calls == 3


def test_tool_call_limit(lab):
    backend = ScriptedBackend([
        {"tool_calls": [{"name": "list_files", "input": {}} for _ in range(5)]},
        {"final": "never reached"},
    ])
    plan = [StageSpec(stage_id="implement", exposed_skill_ids=[],
                      limits=ResourceLimits(max_tool_calls=2))]
    result = run(lab, backend, plan)
    assert result.status is RunStatus.AGENT_LIMIT
    assert result.termination_reason is TerminationReason.TOOL_CALL_LIMIT


def test_backend_error_is_invalid(lab):
    backend = ScriptedBackend([{"error": "provider outage"}])
    result = run(lab, backend, ONE_STAGE)
    assert result.status is RunStatus.INVALID
    assert result.task_success is None
    assert result.termination_reason is TerminationReason.BACKEND_ERROR


def test_invalid_tool_use_is_agent_behavior_not_invalid(lab):
    backend = ScriptedBackend([
        {"tool_calls": [{"name": "read_file", "input": {"path": "../../etc/passwd"}}]},
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "out.txt", "content": "correct"}}]},
        {"final": "done"},
    ])
    result = run(lab, backend, ONE_STAGE)
    assert result.status is RunStatus.COMPLETED  # the error went back to the model
    assert result.task_success is True


def test_two_stage_scripted_run_through_scheduler(lab):
    """Exit criterion: a scripted two-stage run executes through the scheduler."""
    backend = ScriptedBackend([
        # stage 1 writes a draft
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "out.txt", "content": "draft"}}]},
        {"final": "stage 1 done"},
        # stage 2 (fresh context, same workspace) revises it
        {"tool_calls": [{"name": "read_file", "input": {"path": "out.txt"}}]},
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "out.txt", "content": "correct"}}]},
        {"final": "stage 2 done"},
    ])
    plan = [
        StageSpec(stage_id="implement", exposed_skill_ids=["tidy"]),
        StageSpec(stage_id="review", exposed_skill_ids=[]),
    ]
    result = run(lab, backend, plan)
    assert result.status is RunStatus.COMPLETED
    assert result.task_success is True
    assert [s.stage_id for s in result.stage_results] == ["implement", "review"]
    assert [s.worker_id for s in result.stage_results] == ["worker-1", "worker-2"]


def test_events_logged_with_stage_id(lab):
    backend = ScriptedBackend([
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "out.txt", "content": "correct"}}]},
        {"final": "done"},
    ])
    result = run(lab, backend, ONE_STAGE, run_id="run-events")
    events = [json.loads(line) for line in
              open(result.trace_path, encoding="utf-8")]
    types = [e["type"] for e in events]
    assert types[0] == "run_started"
    assert types[-1] == "run_finished"
    assert "skill_loaded" in types
    assert "file_written" in types
    skill_event = next(e for e in events if e["type"] == "skill_loaded")
    assert skill_event["stage_id"] == "implement"
    assert skill_event["payload"]["reason"] == "forced"
    seqs = [e["sequence"] for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_prompt_envelope_never_truncates_silently(lab):
    stage = StageSpec(stage_id="implement", exposed_skill_ids=["tidy"])
    big_body = "x" * (MAX_SYSTEM_PROMPT_CHARS + 1)

    class FakePkg:
        body = big_body

        class snapshot:
            name = "big"
            package_hash = "sha256:0"

    with pytest.raises(PromptEnvelopeError):
        assemble_system_prompt(stage, {"tidy": FakePkg()})


def test_workspace_reset_between_runs(lab):
    backend1 = ScriptedBackend([
        {"tool_calls": [{"name": "write_file",
                         "input": {"path": "leftover.txt", "content": "x"}}]},
        {"final": "done"},
    ])
    run(lab, backend1, ONE_STAGE, run_id="run-a")
    # Second run with the same run_id directory: leftover must be gone.
    backend2 = ScriptedBackend([
        {"tool_calls": [{"name": "list_files", "input": {}}]},
        {"final": "done"},
    ])
    run(lab, backend2, ONE_STAGE, run_id="run-a")
    ws = lab["root"] / "runs" / "run-a" / "workspace"
    assert not (ws / "leftover.txt").exists()
    assert (ws / "input.txt").exists()
