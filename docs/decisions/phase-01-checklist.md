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

## P1.4 Live backend — DONE, with an operator-approved deviation

**Deviation from spec §3.1:** the operator chose a local Ollama backend
instead of the Anthropic API (no API key, no cloud spend). The backend
protocol is unchanged; an Anthropic backend can be added later behind the
same interface. Recorded 2026-09-16.

- [x] Ollama backend behind the backend protocol; official /api/chat
      tool-use format verified against docs before implementation
- [x] Model ID pinned explicitly in campaign config (never `latest` silently);
      reported model identity recorded per response
- [x] Termination classification and per-call usage capture (prompt_eval_count /
      eval_count)
- [x] Server reachability smoke check before any live dispatch; `doctor` reports
      ollama status
- [ ] Wall-clock timeout is checked between model calls; a single hung request
      is bounded by the HTTP client timeout (600s), not preempted mid-request

## P1.5 Campaign planner — DONE for the local-inference model

- [x] Token-budget ledger: cumulative caps, `not_run_budget` persisted for
      unstarted runs, incomplete studies flagged (USD price table is N/A for
      local inference; spend recorded as $0 with `free_local` status)
- [x] Crash-safe persistence and `--resume`: completed identical planned run IDs
      reused, corrupt artifacts re-run, changed configs refused
- [x] Preregistration file + hash binding: live campaigns refuse to run without
      one; hash recorded in study summary and report
- [x] `squelch plan` (never contacts a model)

## P1.6 Constructed conflict — machinery DONE; live exit criterion pending

- [x] Constructed pair: `modernize-thoroughly` (broad edits) vs `minimal-change`
      (minimal diffs, no new files); documented as constructed
- [x] Four-condition grid (none/a/b/ab) with interaction contrasts + Wilson
      intervals; scripted demo shows the full pattern offline
- [ ] **Exit requirement (live): the pair shows reproducible degradation vs.
      both singletons across repetitions on the live model, or the fixture is
      redesigned.** Run `conflict-pilot.yaml` once Ollama + qwen3:8b are ready.
- [ ] Baseline difficulty calibration (0.4–0.8 band) — measured by the same
      pilot's `none` condition

## P1.7 Report — DONE

- [x] Conditions side by side with skills, assertion results, usage, file
      changes (A/M/D + diff.patch artifact), per-run table, event trace paths
- [x] Four-condition interaction analysis with intervals and ceiling/floor
      caveats displayed inline
- [x] Preregistration hash, token totals, spend, reused-run count disclosed
