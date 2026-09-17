"""Every grader must be both passable and discriminating.

A task whose grader cannot be satisfied is a floor effect: it carries no
information about skill composition, exactly like a task everything passes
(spec §5.5 difficulty calibration). These tests pin both ends:

- a known-correct reference solution passes every mandatory assertion
- the untouched starter tree does NOT pass

The reference solutions live under tests/fixtures/ and are never visible to
an agent; they exist only to keep the instrument honest.
"""

from pathlib import Path

import pytest

from squelch.experiments.tasks import load_task_fixture
from squelch.sandbox.envs import LocalEnv
from squelch.sandbox.evaluator import TrustedEvaluator, task_success

ROOT = Path(__file__).resolve().parents[2]
GRADERS = ROOT / "fixtures" / "graders"
TASKS = ROOT / "fixtures" / "tasks"
REFERENCES = ROOT / "tests" / "fixtures" / "reference_solutions"

REFERENCED_TASKS = sorted(p.name for p in REFERENCES.iterdir() if p.is_dir())


@pytest.fixture(scope="module")
def evaluator():
    return TrustedEvaluator(LocalEnv(), GRADERS)


@pytest.mark.parametrize("task_id", REFERENCED_TASKS)
def test_reference_solution_passes(task_id, evaluator, tmp_path):
    fixture = load_task_fixture(TASKS / task_id, GRADERS, environment_image="local:test")
    assertions, _ = evaluator.evaluate(fixture.spec, REFERENCES / task_id)
    failed = [a.assertion_id for a in assertions if a.mandatory and not a.passed]
    assert task_success(assertions), f"{task_id} reference solution failed: {failed}"


@pytest.mark.parametrize("task_id", REFERENCED_TASKS)
def test_starter_does_not_pass(task_id, evaluator):
    fixture = load_task_fixture(TASKS / task_id, GRADERS, environment_image="local:test")
    assertions, _ = evaluator.evaluate(fixture.spec, fixture.starter_dir)
    assert not task_success(assertions), f"{task_id} starter already passes — no task to solve"


@pytest.mark.parametrize("task_id", REFERENCED_TASKS)
def test_grader_is_not_all_or_nothing(task_id, evaluator):
    """The starter should fail some assertions but not every one.

    A grader where the starter fails everything usually means the module
    failed to import, which hides which requirement actually matters.
    """
    fixture = load_task_fixture(TASKS / task_id, GRADERS, environment_image="local:test")
    assertions, _ = evaluator.evaluate(fixture.spec, fixture.starter_dir)
    passed = sum(1 for a in assertions if a.passed)
    assert passed > 0, f"{task_id} starter fails every assertion; grader gives no signal"
