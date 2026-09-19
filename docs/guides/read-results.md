---
title: Read the results
---

# Read the results

Read from the top down: scoreboard, report card, then footage.

## 1. The report (the scoreboard)

```bash
uv run squelch report my-pilot --out report.html
```

Read it in this order:

1. **The disclosure box.** Scripted or live? Is a constructed fixture involved?
2. **Status counts.** Anything other than `completed` needs an explanation before you trust a rate.
3. **Task success by condition.** Rates use the valid denominator.
4. **Condition diagnostics.** If one condition writes far more tokens, or any run was truncated, its rate is confounded with the output cap.
5. **The interaction table**, only after the above.

## 2. Reading an interval

Each pooled rate has a Wilson 95% interval, for example `0.75 [0.47, 0.91]` for 9/12. **If two intervals overlap heavily, the data can't tell those conditions apart.** A visible dip whose interval overlaps its neighbours is a candidate, not a finding.

A `pair_vs_A` of `-0.17` looks like a 17-point loss. With 12 runs per condition it is compatible with no effect at all.

## 3. One run's report card

```text
.squelch/studies/my-pilot/runs/my-pilot-r0038/
  result.json     # status, task_success, assertions, usage, termination
  run_spec.json   # the recipe for this run
  events.jsonl    # ordered events
  diff.patch      # what changed vs. the starter
  workspace/      # the final files
```

```bash
python3 - <<'EOF'
import json
r = json.load(open(".squelch/studies/my-pilot/runs/my-pilot-r0038/result.json"))
print(r["status"], r["task_success"], r["termination_reason"])
for a in r["assertions"]:
    print("PASS" if a["passed"] else "FAIL", a["assertion_id"], "-", a["detail"][:70])
EOF
```

## 4. The footage: `events.jsonl`

One JSON object per line, in order. A quick skim:

```bash
python3 - <<'EOF'
import json
for line in open(".squelch/studies/my-pilot/runs/my-pilot-r0038/events.jsonl"):
    e = json.loads(line)
    print(e["sequence"], e["type"], str(e["payload"])[:70])
EOF
```

Useful things to look for:

- `skill_loaded` events: which skills were really exposed, in which order.
- `model_response` with `stop_reason: length`: the model was cut off.
- `limit_reached`: which limit ended the run.
- `tool_completed` with `is_error: true`: the agent tried something the broker refused.

## 5. When a failure looks dramatic, open the failed runs

The most important habit. In the first pilot one cell read 3/3, 3/3, 3/3, **0/3** for the pair. Opening the three failed runs showed three *unrelated* causes: a cut-off response, literal `\n` characters written into a file, and a docstring closed with the wrong quotes. That's noise landing in one cell, not a conflict.

Before believing a dramatic cell:

1. Read the failed assertions' `detail` text.
2. Check `termination_reason` and `stop_reason` for truncation.
3. Open `diff.patch` and the final file.
4. Ask whether the failures share a cause, or just a cell.

## 6. Re-deriving labels

If you fix a classification rule, don't re-run. Use [`replay`](../architecture/analysis.md#replay-offline-re-analysis) to re-derive labels from the recorded events into a new study.

## Using the published data

The pilot's raw results are in the repository, so you can practise on real data: see [Pilot 001](../results/pilot-001.md#reproduce-it).
