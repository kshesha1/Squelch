---
title: Quickstart (offline demo)
---

# Quickstart: the offline demo

This runs the whole pipeline end to end with **no API key, no network, and no model**. The "agent" is a deterministic script.

## 1. Run a two-condition study

```bash
uv run squelch run \
  --config fixtures/campaigns/offline-demo.yaml \
  --backend scripted \
  --study-id demo
```

Expected output:

```text
study: demo
runs: 8  status counts: {'completed': 8}
artifacts: .squelch/studies/demo
```

That was 4 tasks x 2 conditions (`none` and `skill`) x 1 repetition. For each run Squelch reset a fresh workspace, exposed the skill (or not), replayed the scripted "agent" through the real tool loop, graded the result with a trusted grader, and wrote everything to disk.

## 2. Render the report

```bash
uv run squelch report demo --out report.html
open report.html        # or xdg-open on Linux
```

You'll see status counts and a task-by-condition success table: `none` at 0.00 and `skill` at 1.00 for every task.

## 3. Try the four-condition machinery

```bash
uv run squelch run \
  --config fixtures/campaigns/conflict-demo.yaml \
  --backend scripted \
  --study-id conflict-demo
uv run squelch report conflict-demo --out conflict.html
```

This adds the `none / a / b / ab` design, the interaction contrasts with confidence intervals, a fixture-provenance table, and verbosity diagnostics.

## What you just proved (and what you didn't)

:::warning The result is scripted by construction
In the offline demo the `none` transcripts contain deliberate mistakes and the `skill` transcripts are correct. In the conflict demo the singleton conditions are scripted to pass and the pair to fail.

That shows the **pipeline can detect and correctly describe** such a difference. It says nothing about any real model or real skill. Scripted studies are labelled `evidence_stage: scripted` everywhere they appear.
:::

Two prebuilt reports from these exact commands are in [`examples/demo/`](https://github.com/kshesha1/Squelch/tree/main/examples/demo) if you want to look without running anything.

## Look inside a run

```text
.squelch/studies/demo/
  study.json                    # per-cell counts, status counts, diagnostics
  runs/demo-r0001/
    run_spec.json               # the recipe: task, skills, limits
    result.json                 # the grade, assertion by assertion
    events.jsonl                # ordered observable events
    diff.patch                  # what the agent changed
    workspace/                  # the final files
```

See [reading results](../guides/read-results.md) for a guided tour.

## Next

- Run a real model on your own machine: [live local runs](./live-local-runs.md).
- Understand what happened: [core concepts](../concepts/core-ideas.md).
