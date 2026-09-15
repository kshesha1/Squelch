# Phase 1 implementation checklist

Status as of 2026-09-15. Ticket IDs reference spec.md §6.

## P1.1 Package skeleton — DONE (this pass)

- [x] `pyproject.toml` with `squelch` CLI entry point; distribution name `squelch-skills`
- [x] uv lockfile
- [x] Pydantic v2 schemas for all §4.1 entities, §4.2 events, §4.3 statuses
- [x] Canonical JSON hashing (sorted keys, no non-finite floats) + exact-byte file hashing
- [x] Scripted backend behind the backend protocol
- [x] `squelch doctor`, `validate`, `run` (scripted), `report`
- [x] CI: lint + keyless tests + offline demo; Docker sandbox as a separate job
- [x] Apache-2.0 license, README stating in-progress status and what is (not yet) measured
- [ ] Public repository (local git only; pushing requires separate authorization —
      spec §14.10)
- [ ] Confirm `squelch-skills` is free on PyPI before first release

## P1.2 Skill ingestion — DONE (this pass)

- [x] SKILL.md frontmatter parsing (name, description required)
- [x] Per-file exact-byte hashes; package identity covers reference files
- [x] Symlink and size validation; path-boundary enforcement on resource reads
- [x] Unknown optional metadata preserved as data, never execution authority
- [x] Inventory loader; fixtures `minimal-change`, `edge-case-checklist`

## P1.3 Task engine — DONE for the offline path

- [x] Four task fixtures: json-config, python-repair, api-migration, robust-input
- [x] Trusted evaluator: fresh directory, allowed-output filtering, grader never
      agent-visible, tamper/timeout/garbage-output tests
- [x] DockerEnv implementing the §5.3 container contract; boundary tests in a
      Docker-marked job
- [x] LocalEnv clearly labeled non-isolating for scripted/offline development
- [ ] Pinned task image digest (currently tag `python:3.12-slim`; pin a digest
      before live runs)
- [ ] **Baseline difficulty calibration (0.4–0.8 band) requires live runs — blocked
      on P1.4/P1.5 and a budget. Not verifiable offline; do not claim it.**

## Runner foundation (ahead of P1.4)

- [x] Stage scheduler executing a general `stage_plan`; no single-stage special case
- [x] Forced skill exposure with `skill_loaded` events; no silent truncation
      (planning fails on envelope overflow)
- [x] Tool broker: list_files/read_file/write_file/run_checks, path boundaries,
      allowlisted public checks only
- [x] JSONL event log with stage_id, sequence, termination classification
- [x] Scripted two-stage run through the scheduler (test)

## Remaining before P1.4 is complete

- [ ] Anthropic backend behind the protocol (verify official tool-use docs [S3]
      first; record model ID + SDK version)
- [ ] Per-request event capture of redacted provider request/response bodies
- [ ] Wall-clock timeout enforced around live requests (current timeout check is
      between-call, sufficient for scripted runs only)

## Remaining for P1.5

- [ ] Budget ledger: price table, per-request reservation, stop-when-insufficient,
      `not_run_budget` status
- [ ] Crash-safe persistence and `--resume` (reuse identical planned run IDs only)
- [ ] Preregistration file + hash binding into comparisons
- [ ] `squelch plan` (never contacts a model)

## Remaining for P1.6–P1.7

- [ ] Constructed conflict skill pair + four-condition grid; exit requirement:
      reproducible degradation vs. both singletons
- [ ] Full comparison report: side-by-side conditions, assertions, usage, file
      diff, ordered events (current report is a study summary table)
- [ ] A/A subset; per-run cost measurement; §4.5 budget table update
