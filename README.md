# Squelch

> In radio, the *squelch* circuit suppresses unwanted noise on a channel so
> the signal comes through cleanly.

Squelch is an open-source experimental system for evolving agent skill
collections. It discovers when skills help, interfere, or become
unnecessary, and tests whether changing how their instructions are applied
— ordering, phase separation, or context isolation — improves outcomes.

**Status: work in progress, Phase 1 (instrumented laboratory).**

## What is supported by measurement right now

Nothing yet. The current codebase provides:

- a skill package parser with content-hashed snapshots (a reference-file
  edit changes package identity),
- a bounded tool-calling runner behind a stage-scheduler abstraction,
- a constrained task sandbox contract (Docker) plus a clearly-labeled
  local fallback for offline development,
- a trusted evaluator that grades final artifacts in a fresh directory
  with grader code the agent never sees,
- a deterministic scripted backend and an offline end-to-end demo.

Scripted results validate the harness program only — they are never a
model-performance claim. No live model results exist yet; the Anthropic
backend and campaign planner land with tickets P1.4–P1.5.

## Try the offline demo (no API key, no network)

```bash
uv sync
uv run squelch doctor
uv run squelch validate --config fixtures/campaigns/offline-demo.yaml
uv run squelch run --config fixtures/campaigns/offline-demo.yaml --backend scripted
uv run squelch report <STUDY_ID> --out report.html
```

The `run` command prints the study ID and where artifacts were written
(`.squelch/studies/<study-id>/`): per-run JSONL event traces, run specs,
results, and a study summary.

## Naming

The project, repository, import package, and CLI are all `squelch`. The
PyPI distribution name is `squelch-skills`, because bare `squelch` is
already taken by an unrelated SQL REPL package.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

See [spec.md](spec.md) for the full specification and
[docs/decisions](docs/decisions) for the Phase 1 checklist.

## License

Apache-2.0. Third-party skill and fixture licenses are tracked separately
and do not inherit the project license.
