# Squelch methodology

How this project turns "does a skill help?" into something measurable, and
what each result is and is not allowed to claim.

## 1. What an experiment is here

One **run** = one task, executed once, under one **condition** (a set of
skills exposed in a declared order), graded by trusted code the agent never
sees. A **study** is a grid of runs: tasks x conditions x repetitions.

Conditions are the whole point. To ask whether skills A and B interfere you
need four:

| Condition | Skills exposed |
|---|---|
| `none` | nothing — the baseline |
| `a` | A alone |
| `b` | B alone |
| `ab` | both, in a declared order |

Comparing only `ab` against `none` cannot distinguish "the pair is bad" from
"either one is bad."

## 2. Controls that make a comparison mean something

- **Fresh state per run.** The workspace is rebuilt from the starter tree and
  the conversation starts empty for every run. Nothing leaks between runs.
- **Interleaved condition order.** Within each task/repetition block the
  condition order is shuffled from the schedule seed, so drift in machine
  load or model state cannot line up with one condition.
- **Identical task, limits, and environment across conditions.** Only skill
  exposure varies.
- **A/A trial.** Two conditions with *identical* skill exposure under
  different labels. Whatever gap appears between them is harness noise plus
  model variability — the yardstick a real effect must clear.
- **Forced exposure.** Phase 1 injects skill bodies directly rather than
  letting the model choose to load them, so the experiment measures the
  effect of exposure, not of selection. Those are different questions and are
  never mixed in one study.

## 3. Difficulty calibration

A task that every condition passes, or that every condition fails, carries no
information about composition. Target: the no-skill baseline lands roughly
between 0.4 and 0.8.

This is pinned from both ends:

- **Ceiling** — measured by running the `none` condition and reading the rate.
- **Floor** — pinned in CI by `tests/integration/test_grader_calibration.py`,
  which requires a hidden reference solution to pass every mandatory
  assertion while the untouched starter does not. A grader nobody can satisfy
  is as useless as one everybody satisfies.

## 4. Execution status is not task quality

A run's **status** says whether the machinery worked; `task_success` says
whether the work was correct. They are recorded separately:

| Status | Meaning | Counts in denominator? |
|---|---|---|
| `completed` | agent stopped normally | yes (may pass or fail) |
| `agent_limit` | exhausted model calls, tool calls, time, or output budget | yes, as non-success |
| `invalid` | sandbox, provider, or evaluator failure | no — reported separately |
| `not_run_budget` | never started; budget exhausted | no — reported as incomplete |
| `interrupted` | operator interrupt or host crash | no — partial artifacts kept |

Every report publishes status counts and the valid denominator. An
inconvenient run is never silently replaced.

## 5. Confounds this harness actively watches for

- **Output truncation.** A response cut off by the token cap is classified as
  `agent_limit`, never as a normal finish. Treating truncation as ordinary
  failure would blame the skill for a limits artifact.
- **Verbosity.** More instructions produce more output as well as a longer
  prompt, so a condition can fail by running into the output ceiling rather
  than by reasoning worse. Median and maximum output tokens plus
  truncated-run counts are printed beside every success rate.
- **Prompt length.** Conditions differ in prompt length by construction. The
  spec's answer is a length-matched control arm; Phase 1 does not claim to
  have separated length from content.

## 6. Statistics

- **Primary endpoint:** task success, requiring every mandatory assertion.
- **Intervals:** Wilson score intervals on proportions. They never collapse
  to zero width at 0/n or n/n, and an empty cell yields
  `insufficient_evidence` rather than manufactured precision.
- **Interaction contrasts** on the additive probability scale:
  `pair_vs_A = p(ab) − p(a)`, `pair_vs_B = p(ab) − p(b)`,
  `additive_interaction = p(ab) − p(a) − p(b) + p(none)`.
  These are distorted by ceiling and floor effects, so saturated cells are
  flagged inline. A negative contrast alone does not establish a harmful
  pair.
- **Three repetitions is a debugging default, not a confidence guarantee.**
  At n=3, a 0/3 cell has a 95% interval reaching past 0.5. Screening results
  are descriptive only.

## 7. Evidence stages

Every result carries one:

- `scripted` — deterministic transcripts. Validates the program. **Never** a
  model-performance claim.
- `screening` — live, small N, descriptive. Generates candidates.
- `confirmation` — frozen fixtures, preregistered sample size, fresh calls on
  tasks never used for selection.
- `external_replication` — someone else's machine.

Nothing is promoted across stages automatically.

## 8. Preregistration

A live campaign refuses to start without a preregistration file. Its hash is
recorded in the study summary and printed in the report. Anything analyzed
that was not declared there is exploratory and labeled as such.

## 9. Grader integrity

Grader code lives outside the agent workspace and is never mounted into it.
At evaluation time, only files matching the task's declared `allowed_outputs`
are copied into a fresh directory, and the trusted grader runs there. A
`grade.py` planted by the agent is neither copied nor executed — pinned by
test. Where a task depends on a library, the grader imports its own
instrumented copy rather than the agent's.

## 10. Scope of any claim

Results describe **this runner, this model, these fixtures, on these tasks**.
The runner deliberately exposes its own skill-loading semantics; it is not an
emulation of any commercial coding agent. Authored fixtures establish
pipeline behavior, not ecosystem prevalence. A constructed conflict is
labeled constructed everywhere it appears.
