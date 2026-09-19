---
title: Analysis and replay
---

# Analysis and replay

Two modules: `analysis/effects.py` computes the numbers, and `analysis/replay.py` lets you re-derive labels offline.

## Wilson intervals

`wilson_interval(successes, n, z=1.96)` returns the Wilson score interval for a binomial proportion.

Why Wilson and not the textbook interval: at 0/n or n/n the textbook interval collapses to zero width and claims certainty you don't have. Wilson stays honest at the edges. For example, 0 of 5 gives roughly [0.00, 0.43] rather than a spurious point.

- `n == 0` raises rather than inventing precision. Callers report **`insufficient_evidence`** instead.
- `successes` outside `[0, n]` raises.

## The four-condition contrasts

`four_condition_effects()` takes `{condition_id: (successes, valid_n)}` and returns:

| Field | Definition |
|---|---|
| `pair_vs_a` | `p(ab) - p(a)` |
| `pair_vs_b` | `p(ab) - p(b)` |
| `additive_interaction` | `p(ab) - p(a) - p(b) + p(none)` |
| `notes` | warnings, see below |

Behaviour worth knowing:

- **A missing or empty condition makes the whole comparison `insufficient`**: every contrast is `None`. Nothing is imputed.
- **Ceiling and floor cells are flagged.** If any condition sits at exactly 0.0 or 1.0, a note warns that saturated cells distort the additive contrast.
- The functions are checked against known tables, including the null table where all four conditions are equal (interaction = 0).

## What is *not* implemented

The spec calls for a paired hierarchical bootstrap, multiplicity correction (e.g. Holm) across predeclared confirmatory tests, and non-inferiority testing for release decisions. None exist yet. Phase 1 reports descriptive rates with Wilson intervals only, and labels them `screening`. See the [roadmap](../roadmap.md).

## Replay: offline re-analysis

```bash
uv run squelch replay pilot-001
```

`replay` re-reads a stored study's **recorded events**, re-applies the *current* classification rules, and writes a **new derived study**. It never contacts a model, never re-executes an agent, and never modifies the source.

### Why it exists

A classification rule can be wrong while the underlying observation is fine. The first live pilot recorded `stop_reason: "length"` faithfully but labelled those runs `completed`. Re-running 48 runs to fix a label would burn an hour and produce *different* runs. Re-deriving the label from the recorded event fixes it exactly.

### What it changes, and what it refuses to

- It re-derives each run's **status and termination reason** from its events (limit events, `stop_reason`, error events).
- **Grading is never rewritten.** Assertions and `task_success` for a normal run are untouched; only a run reclassified as an exhausted budget gets `task_success = false`.
- The derived study records `derived_from`, `analysis_version` (`replay/1`), the list of reclassified runs (with before and after), and a disclosure line stating that no model was called.

**It refuses when re-derivation would not be faithful.** The check: if a truncated response *also requested tools*, the corrected runner would have stopped there instead of executing those tools, so the remainder of that run never happened. No amount of re-analysis can invent a run that didn't occur, so replay raises an error instead. In the first pilot there were zero such cases (both truncated responses had no tool calls), so the re-derivation was exact.

### Output

```text
derived study: pilot-001-reanalyzed
runs re-analyzed: 48  reclassified: 2
  pilot-001-r0021: completed/final_response -> agent_limit/output_token_limit
  pilot-001-r0038: completed/final_response -> agent_limit/output_token_limit
status counts: {'completed': 46, 'agent_limit': 2}
no model was called; grading unchanged
```

Each derived run directory holds `result.json`, `run_spec.json` and a `source.json` pointing back at the original. Events, diffs and workspaces stay in the source study. An existing destination study is never overwritten.

You can reproduce exactly this from the published raw data: see [Pilot 001](../results/pilot-001.md#reproduce-it).
