---
title: Troubleshooting
---

# Troubleshooting

Problems we've actually hit, and what they meant.

## `ollama: not reachable` in `doctor`, or "ollama server not reachable" on `run`

The server isn't running. Start it in another terminal:

```bash
ollama serve
```

Then confirm with `uv run squelch doctor`.

## A run is `invalid` with a backend error mentioning the model

The model isn't pulled. Run `ollama pull qwen3:8b` (or whatever `model.id` names).

## Runs suddenly take minutes instead of seconds

**Check memory before suspecting the code.** An 8B model holds ~5.6 GB. If free RAM is a few hundred MB and swap is in use, the model is being paged in and out and single calls can stretch from ~20 s to ~14 min.

- Close memory-heavy apps.
- Don't run tests or other heavy work during a campaign.
- Stop the campaign, free memory, and `--resume`.

## `study 'x' already exists; results are immutable`

Squelch won't overwrite results. Pick a new `--study-id`, or add `--resume` to fill in missing runs of the *same* config.

## `study 'x' was created from a different config`

You changed the campaign file after starting the study. A changed config needs a **new study**; `--resume` only continues an identical one.

## Runs ended as `agent_limit` with `output_token_limit`

The model's response hit `max_output_tokens` and was cut off. That's a limit, not a wrong answer. Options: raise the cap (this changes the config, so start a new study), or look at the [diagnostics table](../architecture/reporting.md) to see whether one condition is systematically more verbose.

## Runs are `invalid` with "evaluator failure"

The trusted grader crashed, timed out, or printed something unparseable. This is deliberately **not** scored as a failure. Run the grader by hand against the run's workspace to see the error:

```bash
python fixtures/graders/<task>/grade.py .squelch/studies/<id>/runs/<run>/workspace
```

## `live campaigns require a 'preregistration' file`

By design. See [preregistration](./preregistration.md). Scripted campaigns are exempt.

## `missing scripted transcript`

A scripted campaign needs `<scripted_transcripts>/<task_id>/<condition_id>.json` for every task and condition in the grid.

## `composition policy 'phased' arrives in Phase 3`

Only `shared` is implemented. Multi-stage policies are on the [roadmap](../roadmap.md).

## Docker tests are deselected or skipped

`pytest -m "not docker"` excludes them on purpose. `pytest -m docker` needs a running daemon and the `python:3.12-slim` image; with no daemon the tests are **skipped**, and a skip is never a pass.

## Everything is fine but I don't trust a number

Good. Open the failed runs ([reading results](./read-results.md#5-when-a-failure-looks-dramatic-open-the-failed-runs)), check status counts, and look at the diagnostics table.
