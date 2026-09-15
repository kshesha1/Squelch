"""Task fixture loading.

A task fixture directory:

```
fixtures/tasks/<task_id>/
  task.yaml     # metadata, allowed outputs, checks, limits
  prompt.md     # the agent-visible task prompt
  starter/      # initial workspace tree (may be empty)
```

Grader code lives separately under ``fixtures/graders/<task_id>/`` and is
never part of the agent-visible fixture (§5.3). The task identity binds
prompt hash, starter tree hash, grader hash, and environment identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from squelch.hashing import hash_text, hash_tree
from squelch.schemas import (
    CheckSpec,
    ResourceLimits,
    TaskSpec,
    TaskSplit,
    check_schema_version,
)


@dataclass(frozen=True)
class TaskFixture:
    spec: TaskSpec
    prompt: str
    starter_dir: Path


def load_task_fixture(
    task_dir: Path, graders_root: Path, *, environment_image: str
) -> TaskFixture:
    task_dir = Path(task_dir)
    meta = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    check_schema_version(str(meta["schema_version"]))

    prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
    starter = task_dir / "starter"
    if not starter.is_dir():
        raise FileNotFoundError(f"task {task_dir.name} is missing a starter/ directory")

    grader_dir = graders_root / meta["task_id"]
    if not (grader_dir / "grade.py").is_file():
        raise FileNotFoundError(f"task {meta['task_id']} has no grader at {grader_dir}")

    checks = [CheckSpec(**c) for c in meta.get("checks", [])]
    limits = ResourceLimits(**meta.get("limits", {}))
    spec = TaskSpec(
        task_id=meta["task_id"],
        family_id=meta["family_id"],
        split=TaskSplit(meta.get("split", "development")),
        prompt_hash=hash_text(prompt),
        starter_tree_hash=hash_tree(starter),
        environment_image=environment_image,
        grader_hash=hash_tree(grader_dir),
        allowed_outputs=list(meta["allowed_outputs"]),
        checks=checks,
        limits=limits,
    )
    return TaskFixture(spec=spec, prompt=prompt, starter_dir=starter)


def load_task_manifest(
    manifest_path: Path, graders_root: Path, *, environment_image: str
) -> list[TaskFixture]:
    """Manifest: ``{schema_version: '1', tasks: [<relative task dir>, ...]}``."""
    manifest_path = Path(manifest_path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    check_schema_version(str(data["schema_version"]))
    fixtures = []
    for rel in data["tasks"]:
        fixtures.append(
            load_task_fixture(
                manifest_path.parent / rel, graders_root, environment_image=environment_image
            )
        )
    ids = [f.spec.task_id for f in fixtures]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate task_ids in manifest: {ids}")
    return fixtures
