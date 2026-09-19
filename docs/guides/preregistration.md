---
title: Preregistration
---

# Preregistration

Before any **live** campaign, declare what you expect and how you'll analyse it. Otherwise it is far too easy to find a story in the data afterwards.

## What it does here

- A live campaign **refuses to start** without a `preregistration:` file.
- The file's hash is recorded in the study summary and shown in the report.
- Any analysis not declared in it is labelled **exploratory** in reports and posts.

## Create one

```bash
uv run squelch prereg --phase 1 --out docs/preregistration/phase-01.yaml
```

This writes a template and **refuses to overwrite** an existing file. It fills in the current git commit. Then fill in the rest.

## What to declare

```yaml
schema_version: '1'
phase_id: 'phase-01'
hypotheses:
  - H1 ...      # what you expect, stated so it can be wrong
  - H2 ...
primary_endpoint: task_success
minimum_useful_effect_pp: 10
planned_n: 48
n_rationale: >-
  4 tasks x 4 conditions x 3 repetitions. Screening only: three repetitions
  are a debugging default, not a confidence guarantee.
analysis_method: descriptive rates with Wilson intervals; screening stage
exclusion_rules:
  - runs with status invalid are excluded from the valid denominator and reported
  - runs with status not_run_budget are reported as incomplete cells, never successes
```

A complete worked example is the one that governed the first pilot: [`docs/preregistration/phase-01.yaml`](https://github.com/kshesha1/Squelch/blob/main/docs/preregistration/phase-01.yaml). It declares a positive-control hypothesis (the constructed pair degrades success relative to each singleton) **and** a calibration hypothesis (baselines land in 0.4 to 0.8). The second one failed, and that failure is reported.

## Commit it *before* running

Squelch records the file's hash, but it does **not** verify that the file was committed to git before the run. The discipline is yours: commit the preregistration first, then reference it from the campaign.

## Honest limits

- The check is "file exists and is hashed", not "file was committed earlier".
- There's no automatic detection of deviations from the declared analysis yet; that's on the [roadmap](../roadmap.md).
- Preregistering doesn't make a small sample large. Screening results stay screening results.
