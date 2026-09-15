
import pytest

from squelch.sandbox.envs import LocalEnv
from squelch.sandbox.evaluator import EvaluationError, TrustedEvaluator, task_success
from squelch.schemas import AssertionOutcome, ResourceLimits, TaskSpec, TaskSplit


def make_task(task_id="t1", allowed=None, timeout=30):
    return TaskSpec(
        task_id=task_id,
        family_id="fam",
        split=TaskSplit.DEVELOPMENT,
        prompt_hash="sha256:0",
        starter_tree_hash="sha256:0",
        environment_image="local:test",
        grader_hash="sha256:0",
        allowed_outputs=allowed or ["*.txt"],
        limits=ResourceLimits(task_timeout_seconds=timeout),
    )


def write_grader(root, task_id, code):
    d = root / task_id
    d.mkdir(parents=True)
    (d / "grade.py").write_text(code)
    return root


PASSING_GRADER = """
import json, sys
from pathlib import Path
sub = Path(sys.argv[1])
ok = (sub / "out.txt").exists()
print(json.dumps({"assertions": [{"id": "out-exists", "passed": ok}]}))
"""


def test_grades_allowed_outputs_only(tmp_path):
    graders = write_grader(tmp_path / "graders", "t1", PASSING_GRADER)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("result")
    (ws / "sneaky.py").write_text("print('not allowed, not copied')")
    ev = TrustedEvaluator(LocalEnv(), graders)
    assertions, _ = ev.evaluate(make_task(), ws)
    assert task_success(assertions)


def test_workspace_grader_tampering_has_no_effect(tmp_path):
    """A grade.py planted in the workspace must never be executed or copied."""
    graders = write_grader(tmp_path / "graders", "t1", PASSING_GRADER)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("result")
    (ws / "grade.py").write_text(
        'import json; print(json.dumps({"assertions": [{"id": "fake", "passed": True}]}))'
    )
    ev = TrustedEvaluator(LocalEnv(), graders)
    assertions, _ = ev.evaluate(make_task(allowed=["*.txt"]), ws)
    assert [a.assertion_id for a in assertions] == ["out-exists"]


def test_missing_output_fails_assertion(tmp_path):
    graders = write_grader(tmp_path / "graders", "t1", PASSING_GRADER)
    ws = tmp_path / "ws"
    ws.mkdir()
    ev = TrustedEvaluator(LocalEnv(), graders)
    assertions, _ = ev.evaluate(make_task(), ws)
    assert not task_success(assertions)


def test_garbage_grader_output_is_evaluation_error(tmp_path):
    graders = write_grader(tmp_path / "graders", "t1", "print('not json')")
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("x")
    ev = TrustedEvaluator(LocalEnv(), graders)
    with pytest.raises(EvaluationError, match="not parseable"):
        ev.evaluate(make_task(), ws)


def test_grader_crash_is_evaluation_error(tmp_path):
    graders = write_grader(tmp_path / "graders", "t1", "raise RuntimeError('boom')")
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("x")
    ev = TrustedEvaluator(LocalEnv(), graders)
    with pytest.raises(EvaluationError, match="grader failed"):
        ev.evaluate(make_task(), ws)


def test_grader_timeout_is_evaluation_error(tmp_path):
    graders = write_grader(
        tmp_path / "graders", "t1", "import time; time.sleep(60)"
    )
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("x")
    ev = TrustedEvaluator(LocalEnv(), graders)
    with pytest.raises(EvaluationError, match="timed out"):
        ev.evaluate(make_task(timeout=2), ws)


def test_zero_assertions_is_evaluation_error(tmp_path):
    graders = write_grader(
        tmp_path / "graders", "t1",
        'import json; print(json.dumps({"assertions": []}))'
    )
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("x")
    ev = TrustedEvaluator(LocalEnv(), graders)
    with pytest.raises(EvaluationError, match="zero assertions"):
        ev.evaluate(make_task(), ws)


def test_symlink_in_output_refused(tmp_path):
    graders = write_grader(tmp_path / "graders", "t1", PASSING_GRADER)
    ws = tmp_path / "ws"
    ws.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    (ws / "out.txt").symlink_to(outside)
    ev = TrustedEvaluator(LocalEnv(), graders)
    with pytest.raises(EvaluationError, match="symlink"):
        ev.evaluate(make_task(), ws)


def test_task_success_ignores_non_mandatory():
    assertions = [
        AssertionOutcome(assertion_id="a", passed=True, mandatory=True),
        AssertionOutcome(assertion_id="b", passed=False, mandatory=False),
    ]
    assert task_success(assertions)
