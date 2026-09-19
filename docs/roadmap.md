---
title: Roadmap and known gaps
sidebar_label: Roadmap
---

# Roadmap and known gaps

Five phases, each a runnable release with a measured experiment and a public write-up. **Only Phase 1 exists.** Everything below it is a plan.

| Phase | Increment | Research question | Status |
|---|---|---|---|
| 1 | Instrumented lab and a reproducible constructed conflict | What changes when a skill is exposed, and can we make a conflict appear on demand? | **Built**; research exit criteria partly unmet |
| 2 | Contextual interaction map | Does combination harm occur with skills not designed to conflict? | Planned |
| 3 | **Composition experiment engine (the core)** | Can changing how skills are applied preserve their benefits? | Planned |
| 4 | Generalization and staleness harness | Does the winning arrangement survive new tasks, a new model, a skill edit? | Planned |
| 5 | Lifecycle workbench | Can a collection respond sensibly to change? | Planned |

If time runs short, **Phase 3's control arms are protected before anything else.**

## Phase 1: what's built

Skill ingestion with content-hashed identity; the bounded agent loop behind a stage scheduler; the trusted evaluator and the constrained sandbox contract; scripted and Ollama backends; the campaign planner with token ledger, resume and preregistration binding; Wilson intervals and four-condition contrasts; verbosity diagnostics; offline replay; and the HTML report. See [architecture](./architecture/overview.md) and the [implementation checklist](./decisions/phase-01-checklist.md).

Phase 1's *research* exit criteria are not all met: the constructed pair hasn't reproduced degradation on a live model, and the baselines of three of four tasks are saturated. See [Pilot 001](./results/pilot-001.md).

## Known gaps in what's built

Honest list, so no one is surprised:

- **Docker isn't wired into `squelch run`.** The container environment is implemented and tested, but campaigns always use `LocalEnv`, so all live results ran in a non-isolating environment.
- **The task image isn't pinned by digest** (it's the `python:3.12-slim` tag).
- **A single hung model request isn't preempted.** The task timeout is checked between calls; one slow call is bounded only by the HTTP timeout (600 s for Ollama).
- **The token ledger is checked between runs**, so a campaign can overshoot a cap by up to one run. There is no per-request reservation.
- **No USD accounting.** Local inference is free; a paid backend would need a price table, and stays `cost_unknown` until it has one.
- **Only `forced` skill loading and only the `shared` policy.** No `discovery` mode, no multi-stage policies.
- **Statistics are descriptive.** No hierarchical bootstrap, no multiplicity correction, no non-inferiority testing.
- **Preregistration is hashed, not verified against git history.** Squelch records the file's hash; it doesn't check the file was committed before the runs.
- **`v2` task baselines aren't measured** (the calibration run was interrupted).
- **The constructed conflict hasn't reproduced** on the live model and likely needs redesign so the two skills demand observably incompatible artifacts.
- **Spec CLI commands not implemented:** `init`, `compare`, `compose`, `generalize`, `lifecycle`, `export`.
- **Timing spread is wide** on a memory-constrained laptop; see [troubleshooting](./guides/troubleshooting.md).

## Next bounded steps

1. Measure the live no-skill baselines of the `v2` tasks and keep only families landing in 0.4 to 0.8.
2. Re-run the A/A trial on a task that isn't at ceiling to get a real noise floor.
3. Redesign the constructed conflict so it demands observably incompatible artifacts.
4. Re-run the four-condition pilot on calibrated tasks with more repetitions.
5. Wire `DockerEnv` into the CLI.

A null or negative result at any of these is a valid outcome and will be published as such.

## Phase 2: does it happen with skills nobody designed to conflict?

Determine whether an observed problem comes from one skill, its combination with another, or selection behaviour, using skills written to be useful, not to collide.

Planned: a four-condition planner over candidate pairs; four benign authored skills (`minimal-change`, `edge-case-checklist`, `migration-guide`, `implementation-review`; the last two don't exist yet); **discovery mode** with explicit `load_skill` and `read_skill_resource` tools, logging catalog visibility, body exposure and reference exposure separately; evidence cards; and a clickable pair matrix filtered by task family, model, loading mode and order, where **grey means untested or inconclusive, never safe**. The constructed pair is re-verified in the same study as a positive control.

**If no natural interaction survives confirmation, ship the map and publish the negative finding.** That is a genuine contribution.

## Phase 3: experiment with better composition (the core)

Test whether the *same* skill content works better applied differently, without rewriting or removing the skills.

| Policy | Semantics |
|---|---|
| `shared` | one worker gets both bodies in declared order |
| `phased` | worker A implements; a *fresh* worker B receives the workspace and a bounded handoff, then reviews using B only |
| `isolated` | A and B solve independently from separate workspaces; a no-skill integrator merges bounded diffs |

**Mandatory control arms** appear in the primary results table, never an appendix:

- a **no-skill stage-matched control** (same stage structure and budget, zero skills), so that if it matches the treatment, the gain came from extra attempts rather than instruction separation;
- a **matched-prompt inline arm**, so context isolation and prompt framing don't vary together.

Cost parity is reported two ways (equal total budget; equal per-worker budget), and a policy winning under only one is reported as conditional. **A null result is publishable** provided the control arms ran.

## Phase 4: does the finding survive change?

Take the winning arrangement across three axes: **held-out tasks**, **a second model**, and **a skill edit**, each with the same control arms. Staleness is *computed from identity changes*, not asserted, and a referenced-file edit invalidates a decision even when `SKILL.md` is unchanged. Output is a holds/breaks matrix with an explicit `insufficient_evidence` state and the cost of revalidation.

## Phase 5: close the lifecycle loop

Propose a change, run the relevant experiments, review a scoped decision, promote a configuration, and roll it back reproducibly. Snapshots, a change classifier, a decision policy (coverage, non-inferiority margin, cost ceiling, critical assertions, maximum evidence age), atomic promotion and rollback, and a timeline. Lifecycle management for skill libraries is a crowded area; Squelch claims no novelty in the concept. Its contribution is narrower: decisions are **gated on measured composition and transfer evidence with declared margins, and expire automatically when identities change**.

Automatic instruction synthesis, marketplaces, hosted dashboards and automated external deployment are explicitly out of scope.
