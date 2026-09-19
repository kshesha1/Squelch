---
title: "Pilot 001: results"
sidebar_label: Pilot 001
---

# Pilot 001: what was measured

:::caution TL;DR
**No conflict was demonstrated.** The pair scored lower than either skill alone, in the direction the preregistered hypothesis predicted, but with 12 runs per condition that can't be told apart from noise. The one dramatic-looking cell was three unrelated failures. The pilot also exposed a bug in the lab itself and showed that three of four tasks were too easy to be informative.
:::

This is **`screening`** evidence: small N, one local model, authored fixtures, descriptive only. It describes this runner, not coding agents in general. Preregistration: [`docs/preregistration/phase-01.yaml`](https://github.com/kshesha1/Squelch/blob/main/docs/preregistration/phase-01.yaml).

## Setup

| | |
|---|---|
| Model | `qwen3:8b` via Ollama 0.34.0, temperature 0.2, 2048 output tokens per call |
| Environment | `local:python-3.13.14:darwin`, the **non-isolating** local runner |
| Design | 4 tasks x 4 conditions (`none`, `a`, `b`, `ab`) x 3 repetitions = **48 runs** |
| Skills | `a` = `modernize-thoroughly` (constructed conflict fixture), `b` = `minimal-change`, `ab` = both, in that order |
| Status | 46 `completed`, 2 `agent_limit`, 0 `invalid` |
| Cost | $0.00; 81,624 input and 78,871 output tokens in total |
| Time | median 94 s, mean 223 s per run; about 3 hours in total |

## Results

Successes over valid runs:

| Task | none | a (modernize) | b (minimal) | ab (pair) |
|---|---|---|---|---|
| api-migration | 1/3 | 3/3 | 3/3 | 3/3 |
| json-config | 3/3 | 3/3 | 2/3 | 3/3 |
| python-repair | 3/3 | 2/3 | 3/3 | 3/3 |
| robust-input | 3/3 | 3/3 | 3/3 | **0/3** |

Pooled, with Wilson 95% intervals:

| Condition | Rate | 95% CI |
|---|---|---|
| none | 0.83 (10/12) | [0.55, 0.95] |
| a | 0.92 (11/12) | [0.65, 0.99] |
| b | 0.92 (11/12) | [0.65, 0.99] |
| ab | 0.75 (9/12) | [0.47, 0.91] |

`pair_vs_A = -0.167`, `pair_vs_B = -0.167`, `additive_interaction = -0.250`.

**The direction matches the hypothesis and the evidence does not support it.** Every interval overlaps every other. With 12 runs per condition these contrasts are compatible with no effect, and with an effect in either direction.

## Why the dramatic cell is not a finding

`robust-input` under the pair reads 3/3, 3/3, 3/3, **0/3**, which looks like textbook interference. Opening the three failed runs shows **three unrelated causes**:

| Run | What happened |
|---|---|
| `r0038` | The response was **cut off by the output-token cap** (2,048 tokens) and wrote nothing |
| `r0043` | The model wrote **literal `\n` escape sequences** instead of newlines, producing an unterminated string |
| `r0045` | It closed a docstring with `"` instead of `"""`, a syntax error |

Those are mundane, independent stumbles, not a coherent response to conflicting instructions. The same escape-sequence quirk also appeared once under `b` alone (in `json-config`), so it's a low-rate model behaviour the pair didn't provoke. A 0/3 cell has a Wilson interval reaching past 0.5.

**Recorded as: not a conflict.**

## One real signal, and it's a confound

Output tokens per run are a **total across all of that run's model calls**, so the table separates how many calls a run makes from how long each response is:

| Condition | Median output tokens / run | Median model calls / run | Mean output tokens / call | Runs truncated |
|---|---|---|---|---|
| none | 1,511 | 2.0 | 574 | 0/12 |
| b | 1,530 | 3.0 | 537 | 0/12 |
| a | 1,648 | 2.5 | 677 | 1/12 |
| ab | 2,020 | 3.0 | 718 | 1/12 |

The pair writes about **a third more per run** than the baseline (+34%). That comes from *both* more calls (median 3 vs 2) *and* longer responses (718 vs 574 tokens per call). The longer responses track `modernize-thoroughly`, and **both truncations occurred in conditions that include it**.

So a condition can fail by hitting the output cap rather than by reasoning worse. Phase 1 does **not** separate length from content; that needs the planned length-matched control arm. This table is now printed beside every success rate in the [report](../architecture/reporting.md).

## The instrument was wrong

Investigating `r0038` exposed a bug in the runner. When Ollama returned `stop_reason: "length"` (the model cut off mid-generation), the runner recorded a normal `completed` / `final_response`. The spec classifies an exhausted output budget as `agent_limit`. A hard limit was being disguised as the model simply doing badly. Two of 48 runs were affected.

It was fixed, with a regression test naming the run that exposed it. And rather than re-run the whole pilot, the fix was applied by **offline re-analysis**: the recorded observation was sound and only the derived label was wrong. [`squelch replay`](../architecture/analysis.md#replay-offline-re-analysis) re-derives labels from stored events into a new study, and refuses if a truncated response also requested tools (in which case the corrected runner would have stopped instead, and the rest of that run never happened). Zero such cases existed, so the re-derivation was exact.

The headline rates were **identical before and after** the correction; what changed is the label on two runs.

## Calibration failed

The preregistration's second hypothesis was that each family's no-skill baseline would land in 0.4 to 0.8. It did not: `json-config`, `python-repair` and `robust-input` all scored **3/3 with no skills**; only `api-migration` (1/3) was informative. A task everything passes can't show a skill effect, so most of this grid was uninformative before it ran.

## The A/A trial

`aa-001` ran the same skill (`minimal-change`) under two labels, `aa1` and `aa2`, on `python-repair` and `api-migration`, three repetitions each. Result: **6/6 vs 6/6**, all `completed`.

That is consistent with low noise, but both tasks were at or near ceiling under this skill, so it **cannot bound the noise level**. It is not a noise floor.

## The harder v2 tasks

`json-config-v2`, `python-repair-v2` and `robust-input-v2` were written to fix the calibration problem, and are grader-calibrated (a hidden reference passes; the starter fails). A live calibration run of their no-skill baselines was **stopped at 13 of 20 runs** when the model server was shut down. In the 13 that finished:

| Task | Passed | Ended at a limit |
|---|---|---|
| json-config-v2 | 5/5 | 0 |
| python-repair-v2 | 2/5 | 3 |
| robust-input-v2 | 0/2 | 2 |

That is **not a calibration result**. It's incomplete, and the data isn't published. It suggests the harder variants may be *too* hard or limit-bound, which is exactly what a completed calibration would settle.

## What this does and doesn't show

**It shows:** the pipeline works end to end on a real model; it can catch its own errors; a tempting result was checked and rejected; the tasks needed retuning.

**It does not show:** that skills interfere, that the constructed pair conflicts on this model, or anything about other models or real-world skills.

## Reproduce it

The raw data is committed under [`examples/pilot-001/`](https://github.com/kshesha1/Squelch/tree/main/examples/pilot-001): every run's result, spec, event trace and diff (no workspaces), plus the re-analysed summary and the A/A trial.

```bash
mkdir -p .squelch/studies
cp -r examples/pilot-001/pilot-001 .squelch/studies/

uv run squelch replay pilot-001                     # re-derives labels; contacts nothing
uv run squelch report pilot-001-reanalyzed --out pilot.html
```

You should see `runs re-analyzed: 48  reclassified: 2`. Every numeric claim made publicly is mapped to its source artifact in [`docs/weekly/claims.json`](https://github.com/kshesha1/Squelch/blob/main/docs/weekly/claims.json).

The full narrative, including what was learned, is in the [week 1 report](../weekly/week-01.md).
