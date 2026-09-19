---
title: Experiment design
---

# Experiment design

Squelch's job is to make a comparison mean something. This page explains each design choice and the trap it avoids. The full statement of what each result may claim is in the [methodology](../methodology.md).

## The four-condition design

To test whether skills A and B interfere, every task runs under `none`, `a`, `b` and `ab`.

With `p0, pA, pB, pAB` as the mean task success under the four conditions:

```text
pair_vs_A            = pAB - pA
pair_vs_B            = pAB - pB
additive_interaction = pAB - pA - pB + p0
```

A negative interaction on its own does **not** establish a harmful pair. The contrast lives on the additive probability scale and is distorted by ceiling and floor effects, so saturated cells are flagged next to it. To say "each useful alone, harmful together" you need data supporting *every* part of that sentence.

## Controls

**Fresh state per run.** The workspace is rebuilt from the starter tree and the conversation starts empty. Nothing leaks between runs.

**Interleaved condition order.** Within each task/repetition block the order of conditions is shuffled from a fixed seed. If you always ran `none` first, any drift in machine load or model state would line up with one condition. A fixed seed makes the shuffle reproducible.

**Identical task, limits and environment across conditions.** Only skill exposure varies.

**Forced exposure.** Phase 1 injects the skill body directly into the system prompt, in declared order. That measures the effect of *exposure*. Letting the model choose whether to read a skill (`discovery` mode) measures selection plus behavior, a different question that must never be mixed into the same study. Only `forced` is implemented today.

**An A/A trial.** Two conditions with *identical* skill exposure under different labels. Whatever gap appears between them is harness noise plus model variability, the yardstick any real effect must clear.

## Difficulty calibration

A task that every condition passes, or that every condition fails, carries no information about composition. The target is a no-skill baseline roughly between 0.4 and 0.8.

This is pinned from both ends:

- **Ceiling** is measured by running the `none` condition and reading the rate.
- **Floor** is pinned in CI by [`test_grader_calibration.py`](https://github.com/kshesha1/Squelch/blob/main/tests/integration/test_grader_calibration.py): a hidden reference solution must pass every mandatory assertion, while the untouched starter must not. A grader nobody can satisfy is as useless as one everybody satisfies.

In the first pilot, three of four task families sat at a 1.00 no-skill baseline. See [Pilot 001](../results/pilot-001.md).

## Confounds the harness watches for

| Confound | Why it matters | What Squelch does |
|---|---|---|
| **Output truncation** | A response cut off by the token cap looks like the model failing | Classified as `agent_limit`, never as a normal finish |
| **Verbosity** | More instructions produce more output, so a condition can fail by hitting the ceiling | Median/max output tokens and truncated-run counts printed beside every rate |
| **Prompt length** | Conditions differ in prompt length by construction | Not separated in Phase 1; the planned length-matched arm addresses it |
| **Ceiling / floor** | Saturated cells distort the interaction contrast | Flagged inline in the report |

## Statistics, briefly

- Proportions get **Wilson score intervals**. They never collapse to zero width at 0/n or n/n, and an empty cell yields `insufficient_evidence` rather than manufactured precision.
- **Three repetitions is a debugging default, not a confidence guarantee.** At n=3 a 0/3 cell has a 95% interval reaching past 0.5.
- What is *not* implemented yet: hierarchical bootstrap, multiplicity correction, and non-inferiority testing. See the [roadmap](../roadmap.md).

## Evidence stages

| Stage | Meaning |
|---|---|
| `scripted` | Deterministic transcripts. Validates the program. **Never** a model-performance claim. |
| `screening` | Live, small N, descriptive. Generates candidates. |
| `confirmation` | Frozen fixtures, preregistered sample size, fresh calls on tasks never used for selection. |
| `external_replication` | Someone else's machine. |

## Preregistration

A live campaign won't start without a preregistration file, and its hash is stamped into every result. Anything analysed that wasn't declared there is exploratory and labelled so. See [preregistration](../guides/preregistration.md).
