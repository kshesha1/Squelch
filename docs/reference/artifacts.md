---
title: Artifacts and study layout
---

# Artifacts and study layout

Everything a study produces lives under `.squelch/studies/<study-id>/` (git-ignored). Artifacts are **immutable**: a study is written once.

```text
.squelch/studies/<study-id>/
  study.json
  runs/
    <study-id>-r0001/
      run_spec.json
      result.json
      events.jsonl
      diff.patch
      workspace/
```

## `study.json`

| Field | Meaning |
|---|---|
| `campaign`, `config_hash` | which recipe produced it |
| `backend`, `model_id` | who did the work |
| `evidence_stage` | `scripted`, `screening`, ... |
| `environment` | e.g. `local:python-3.13.14:darwin` |
| `runner_version` | Squelch version |
| `preregistration_hash` | hash of the preregistration file, or `null` for scripted |
| `status_counts`, `total_runs`, `reused_runs` | how the runs ended |
| `usage_totals` | cumulative `input_tokens` / `output_tokens` |
| `spend_usd` | `0.0`: local and scripted inference cost nothing |
| `cells[]` | per task and condition: `n`, `successes`, `valid_n`, `runs[]` |
| `condition_diagnostics[]` | per condition: `n`, `median_output_tokens`, `max_output_tokens`, `median_model_calls`, `mean_output_tokens_per_call`, `truncated_runs` |
| `fixture_provenance[]`, `constructed_fixtures[]` | where each exposed skill came from |
| `disclosure` | plain-English statement of what the evidence is and isn't |
| `generated_at` | UTC timestamp |

A study produced by [`replay`](../architecture/analysis.md#replay-offline-re-analysis) adds `derived_from`, `analysis_version`, and `reclassified_runs[]` (each with `was` and `now`).

## `run_spec.json`

The recipe for one run: `run_id`, `study_id`, `condition_id`, the full `task` (with prompt, starter-tree and grader hashes), the `collection` (ordered skill hashes, policy, loading mode, prompt and tool-schema hashes, runner version), the `model`, `repetition`, `schedule_seed`, the `stage_plan`, and `created_at`.

## `result.json`

| Field | Meaning |
|---|---|
| `status` | `completed`, `agent_limit`, `invalid`, `not_run_budget`, `interrupted` |
| `task_success` | `true`, `false`, or `null` when there's no valid grade |
| `assertions[]` | `assertion_id`, `passed`, `mandatory`, `detail` |
| `termination_reason` | why the loop ended |
| `usage` | input, output, cache-read, cache-write tokens (totals across the run's model calls) |
| `spend_usd`, `spend_status` | `0.0` with `free_scripted` or `free_local`; otherwise `cost_unknown` |
| `artifact_hashes` | `final_workspace`, `evaluated_outputs`, `run_spec`, `diff_patch` |
| `stage_results[]` | per stage: worker id, exposed skills, model and tool calls, usage, termination |
| `changed_files[]` | `A path` / `M path` / `D path` against the starter tree |
| `trace_path` | path of `events.jsonl` |
| `error` | set for `invalid`, `interrupted`, `not_run_budget` |
| `started_at`, `finished_at` | UTC timestamps |
| `metrics` | reserved; empty in Phase 1 |

## `events.jsonl`

One [event](../architecture/data-contracts.md#events) per line, in order.

## `diff.patch`

A unified diff of the final workspace against the starter tree, for every added, modified or deleted file. Binary or oversized files are noted, not diffed.

## `workspace/`

The final files the agent left behind. Grading does **not** run against this directory directly; allowed outputs are copied to a fresh directory first. See [evaluation](../architecture/evaluation.md).

## What gets published

Only explicitly selected, redacted bundles are committed, under [`examples/`](https://github.com/kshesha1/Squelch/tree/main/examples): results, run specs, events and diffs, **without** workspaces. `.squelch/` itself is never committed.
