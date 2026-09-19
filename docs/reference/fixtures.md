---
title: Fixture inventory
---

# Fixture inventory

Everything under [`fixtures/`](https://github.com/kshesha1/Squelch/tree/main/fixtures). All of it is **authored** for this harness. These fixtures establish pipeline behaviour, **not** ecosystem prevalence, and every report says so.

## Skills

| Skill id | What it says | Provenance in metadata |
|---|---|---|
| `minimal-change` | Read first; change only the lines the task requires; never create unrelated files; list changed files before finishing | undeclared |
| `edge-case-checklist` | Before finishing, walk boundary values, empty inputs, declared invalid inputs and off-by-one cases; run public checks | undeclared |
| `modernize-thoroughly` | When you touch a file, modernize the *entire* file, extract reusable logic into helper modules, add a module docstring, and comment anything you couldn't modernize | **`constructed-conflict-fixture`** |

`modernize-thoroughly` is a **deliberately constructed conflict fixture**. Its instructions are individually reasonable but collide with `minimal-change` by design (whole-file rewrites and new helper modules vs. no edits beyond the task and no new files). It is labelled constructed in every study summary and report. It says nothing about how often real skills conflict.

`edge-case-checklist` is not used by any shipped campaign yet; it is reserved for Phase 2.

## Tasks

| Task | Family | What the agent is asked to do | Assertions |
|---|---|---|---|
| `json-config` | json-configuration | Create `config.json` with exactly `name` (non-empty string), `port` (int 1024 to 65535), `debug` (bool); no other files; leave `README.txt` unchanged | up to 8 |
| `python-repair` | small-python-repair | `in_range(x, low, high)` documents inclusive bounds but uses `low < x <= high`; fix it | 8 |
| `api-migration` | api-migration | `app.py` calls the removed `toylib.get(url, 5)`; migrate to `toylib.fetch(url, timeout=...)` and keep the 5-second timeout. Grader uses its own instrumented `toylib` | 5 |
| `robust-input` | robust-input-handling | `parse_int_list` must tolerate `None`, empty, whitespace-only and invalid tokens while keeping valid behaviour | 10 |
| `json-config-v2` | json-configuration | Nested config: `service`, a sorted/distinct/lowercase `features` list, `limits` with a `timeout_ms` that is a multiple of 100, and a `feature_count` equal to the list's length | 16 |
| `python-repair-v2` | small-python-repair | `clamp_and_scale` has **two interacting bugs**: it mutates the caller's list, and it mishandles the upper bound | 11 |
| `robust-input-v2` | robust-input-handling | `parse_spec` must expand ranges (`3-5`), skip descending and malformed ranges, tolerate whitespace, support negatives, and dedupe preserving order | 18 |

The `v2` tasks were written because three of four `v1` tasks sat at a 1.00 no-skill baseline on the pilot model. They are **grader-calibrated** (a hidden reference passes, the starter fails) but their **live baselines are not established**: the calibration run was stopped at 13 of 20 runs. See [Pilot 001](../results/pilot-001.md#the-harder-v2-tasks).

### Manifests

| Manifest | Tasks |
|---|---|
| `development.yaml` | `json-config`, `python-repair`, `api-migration`, `robust-input` |
| `conflict-demo.yaml` | `python-repair`, `api-migration` |
| `calibration-v2.yaml` | `json-config-v2`, `python-repair-v2`, `robust-input-v2`, `api-migration` |

## Campaigns

| Campaign | Backend | Conditions | Reps | Purpose |
|---|---|---|---|---|
| `offline-demo` | scripted | `none`, `skill` (`minimal-change`) | 1 | pipeline self-test, 4 tasks |
| `conflict-demo` | scripted | `none`, `a`, `b`, `ab` | 1 | four-condition machinery, 2 tasks |
| `conflict-pilot` | ollama `qwen3:8b` | `none`, `a`, `b`, `ab` | 3 | the first live pilot, 4 tasks, 48 runs |
| `aa-trial` | ollama `qwen3:8b` | `aa1`, `aa2` (both `minimal-change`) | 3 | A/A noise check, 2 tasks, 12 runs |
| `calibration-v2` | ollama `qwen3:8b` | `none` | 5 | baselines of the `v2` tasks, 20 runs |

In the four-condition campaigns, `a` is `modernize-thoroughly`, `b` is `minimal-change`, and `ab` exposes them in that order.

### Scripted transcripts

`offline-demo` and `conflict-demo` each ship 8 transcripts under `fixtures/campaigns/scripted/`. They are written by hand: in `offline-demo` the `none` transcripts contain deliberate mistakes; in `conflict-demo` the singletons succeed and the pair fails. **That is scripted by construction**, and shows the pipeline can detect such a difference, nothing more.

## Graders

One `grade.py` per task under `fixtures/graders/<task_id>/`. The `api-migration` grader also ships its own `toylib.py`. **The agent never sees any of it.**

## Reference solutions

`tests/fixtures/reference_solutions/` holds hidden correct solutions for the `v2` tasks, used only by the calibration tests.
