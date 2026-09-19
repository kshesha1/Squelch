---
title: Write a task and grader
---

# Write a task and grader

A task has two halves that must never meet: an **agent-visible fixture** and a **trusted grader**.

```text
fixtures/tasks/my-task/
  task.yaml         # metadata, allowed outputs, public checks, limits
  prompt.md         # what the agent is told
  starter/          # the workspace the agent begins with (may be near-empty)
fixtures/graders/my-task/
  grade.py          # trusted; the agent never sees this
```

The grader directory name must equal the `task_id`.

## `task.yaml`

```yaml
schema_version: '1'
task_id: python-repair
family_id: small-python-repair
split: development
allowed_outputs: ["ranges.py"]
checks:
  - check_id: smoke
    cmd: ["python", "-c", "import ranges; print(ranges.in_range(5, 1, 10))"]
    public: true
```

| Key | Meaning |
|---|---|
| `task_id`, `family_id` | identity; a *family* groups related tasks for later analysis |
| `split` | `development` or `held_out` |
| `allowed_outputs` | glob patterns of files the grader will look at. Everything else is ignored |
| `checks[]` | commands the agent may run through `run_checks`. Only `public: true` checks are callable |
| `limits` | optional overrides for the per-task resource limits |

A command of `python` resolves to the interpreter running Squelch. The agent can only run a check by **id**, never an arbitrary command.

## The prompt and starter

Write `prompt.md` as if to a colleague: state requirements explicitly, including what *not* to do ("Do not create any other files"). Put the files the agent starts with in `starter/`.

Identity binds the prompt hash, the starter-tree hash, the grader hash and the environment. Edit any of them and it's a different task.

## The grader

`grade.py` is run as `python trusted/grade.py submission` inside a fresh directory, where `submission/` holds only your `allowed_outputs`. It must print one JSON document:

```python
import json, sys
from pathlib import Path

submission = Path(sys.argv[1])
assertions = []

def add(aid, passed, detail="", mandatory=True):
    assertions.append({"id": aid, "passed": bool(passed),
                       "mandatory": mandatory, "detail": detail})

target = submission / "config.json"
add("config-exists", target.is_file(), "config.json missing")
# ... more assertions ...

print(json.dumps({"assertions": assertions}))
```

Guidelines:

- **Many small assertions beat one big one.** A failed run then tells you *which* requirement failed.
- **Put the reason in `detail`.** It appears in the report.
- **Don't crash on missing files.** Catch import errors and report a failed assertion instead. A crash makes the run `invalid`, not a failure.
- **Grade behavior, not text.** Import the module and call it; don't grep the source.
- **Guard against cheating.** `no-unrelated-files` and "README unchanged" style checks catch the agent editing what it shouldn't.
- **Import your own copy of any library** the task depends on, so the agent can't fake it. See the `api-migration` grader.

## Register it in a manifest

```yaml
# fixtures/tasks/my-manifest.yaml
schema_version: '1'
tasks:
  - my-task
```

Paths are relative to the manifest. Duplicate task ids are rejected.

## Calibrate it

A task is only useful if it's **passable and discriminating**. Add a hidden reference solution:

```text
tests/fixtures/reference_solutions/my-task/    # files a correct agent would leave
```

[`test_grader_calibration.py`](https://github.com/kshesha1/Squelch/blob/main/tests/integration/test_grader_calibration.py) discovers every directory there and asserts that:

1. the reference solution passes every mandatory assertion,
2. the untouched starter does not,
3. the starter still passes *some* assertions (the grader gives partial signal).

You can also run a grader by hand against any directory:

```bash
python fixtures/graders/my-task/grade.py path/to/candidate
```

Then measure the **live no-skill baseline** and aim for roughly 0.4 to 0.8. In the first pilot, three of four tasks were at 1.00, which is why they carried no information. See [experiment design](../concepts/experiment-design.md#difficulty-calibration).

:::warning Executing agent code
With `LocalEnv`, graders import and run code the *model* wrote, on your machine. Only run authored, benign tasks. See [tools and sandbox](../architecture/tools-and-sandbox.md).
:::
