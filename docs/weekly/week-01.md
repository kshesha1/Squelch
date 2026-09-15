# Week 01 — building the laboratory (in progress)

**Question investigated:** none yet — this week is infrastructure. The
research question ("what changes when a skill is exposed?") requires the
live backend (P1.4) and campaign planner (P1.5), which are not built yet.

## What shipped (P1.1–P1.3 + runner foundation)

- Python package `squelch` (distribution `squelch-skills`), Apache-2.0,
  uv-locked, CI with a keyless test job and a separate Docker sandbox job.
- Schemas for every §4.1 entity, §4.2 JSONL events, §4.3 execution
  statuses kept separate from task quality.
- Skill ingestion with content-hashed package identity; editing a
  reference file changes the package hash (tested).
- Stage scheduler executing a general stage plan; Phase 1 uses length 1;
  a scripted two-stage run passes through the same scheduler (tested).
- Tool broker with path-boundary enforcement and allowlisted public
  checks; trusted evaluator grading only allowed outputs in a fresh
  directory with grader code the agent never sees (tamper test included).
- Scripted backend and a fully offline demo: 4 tasks x 2 conditions,
  deterministic transcripts, JSONL traces, study summary, HTML report.

**Reproduction:**

```bash
uv sync
uv run pytest -q -m "not docker"
uv run squelch run --config fixtures/campaigns/offline-demo.yaml --backend scripted --study-id demo
uv run squelch report demo --out report.html
```

## Verification record

- 57 keyless tests passing (hashing, skill identity, path escapes, grader
  tampering/timeout/garbage output, termination statuses, two-stage
  scheduling, campaign interleaving, report HTML escaping).
- Docker boundary tests (network off, read-only root, read-only mount)
  run as a separate marked job; skipped-not-passed when Docker is absent.

## Fixture provenance

All skills and tasks are authored controls written for this harness.
Scripted transcripts are deterministic program fixtures. **No live model
was called; no finding about skills exists yet.** The offline demo's
none-vs-skill difference is scripted by construction — it validates that
the pipeline can register a difference, nothing more.

## Spend

$0. No paid inference has run.

## Limitations and next step

- Task difficulty calibration (0.4–0.8 no-skill baseline band) cannot be
  checked offline; it is the first thing to measure once P1.4 lands.
- LocalEnv is not an isolation boundary and is labeled as such in every
  artifact it produces; live runs will use the Docker environment with a
  pinned image digest.
- Next bounded task: P1.4 — Anthropic backend behind the existing
  protocol, after verifying the official tool-use documentation.
