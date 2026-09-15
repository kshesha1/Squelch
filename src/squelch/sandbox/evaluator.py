"""Trusted evaluator (ticket P1.3).

Evaluates a run's final workspace in a *fresh* directory with trusted
grader code. Contracts enforced here (spec §5.3):

- Grader code is never mounted into the agent workspace; it lives under
  ``fixtures/graders`` and is copied to a separate directory at evaluation
  time.
- Only files matching the task's ``allowed_outputs`` globs are copied out
  of the agent workspace, so a modified test file or workspace helper
  cannot influence grading unless the task explicitly allows that path.
- The grader emits a single JSON document on stdout:
  ``{"assertions": [{"id": ..., "passed": bool, "mandatory": bool, "detail": str}]}``.
  Anything else is an evaluator failure -> run status ``invalid``.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from squelch.hashing import hash_tree
from squelch.sandbox.envs import ExecutionEnvironment
from squelch.schemas import AssertionOutcome, TaskSpec


class EvaluationError(RuntimeError):
    """Evaluator infrastructure failure — maps to run status `invalid`."""


def collect_allowed_outputs(workspace: Path, allowed_globs: list[str]) -> list[str]:
    """Relative paths in the workspace matching the allowed-output globs."""
    selected: set[str] = set()
    for pattern in allowed_globs:
        for p in workspace.glob(pattern):
            if p.is_symlink():
                raise EvaluationError(f"symlink in agent output refused: {p}")
            if p.is_file():
                selected.add(p.relative_to(workspace).as_posix())
    return sorted(selected)


class TrustedEvaluator:
    def __init__(self, env: ExecutionEnvironment, graders_root: Path):
        self.env = env
        self.graders_root = Path(graders_root)

    def grader_dir(self, task_id: str) -> Path:
        d = self.graders_root / task_id
        if not (d / "grade.py").is_file():
            raise EvaluationError(f"missing grader for task {task_id}: {d}/grade.py")
        return d

    def evaluate(self, task: TaskSpec, workspace: Path) -> tuple[list[AssertionOutcome], str]:
        """Grade the final workspace. Returns (assertions, evaluated_tree_hash)."""
        grader = self.grader_dir(task.task_id)
        with tempfile.TemporaryDirectory(prefix="squelch-eval-") as tmp:
            eval_root = Path(tmp)
            submission = eval_root / "submission"
            trusted = eval_root / "trusted"
            submission.mkdir()
            shutil.copytree(grader, trusted)

            rel_files = collect_allowed_outputs(workspace, task.allowed_outputs)
            for rel in rel_files:
                dst = submission / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(workspace / rel, dst)
            evaluated_hash = hash_tree(submission, relative_paths=rel_files)

            result = self.env.run(
                ["python", "trusted/grade.py", "submission"],
                workspace=eval_root,
                timeout_seconds=task.limits.task_timeout_seconds,
            )
            if result.timed_out:
                raise EvaluationError(f"grader timed out for task {task.task_id}")
            if result.exit_code != 0:
                raise EvaluationError(
                    f"grader failed for task {task.task_id}: "
                    f"exit={result.exit_code} stderr={result.stderr[:2000]}"
                )
            try:
                payload = json.loads(result.stdout)
                raw = payload["assertions"]
                assertions = [
                    AssertionOutcome(
                        assertion_id=a["id"],
                        passed=bool(a["passed"]),
                        mandatory=bool(a.get("mandatory", True)),
                        detail=str(a.get("detail", "")),
                    )
                    for a in raw
                ]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise EvaluationError(
                    f"grader output not parseable for task {task.task_id}: {exc}; "
                    f"stdout={result.stdout[:2000]}"
                ) from exc
            if not assertions:
                raise EvaluationError(f"grader returned zero assertions for task {task.task_id}")
            return assertions, evaluated_hash


def task_success(assertions: list[AssertionOutcome]) -> bool:
    """Primary endpoint: all mandatory assertions pass (§5.5)."""
    return all(a.passed for a in assertions if a.mandatory)
