# Phase 1 implementation checklist

Ticket IDs reference spec.md §6. Last updated 2026-09-17.

## Recorded deviations from the spec

1. **Live backend is Ollama, not the Anthropic API** (spec §3.1). The
   operator chose local inference: no API key, no cloud spend, model runs on
   the host. The backend protocol is unchanged, so a hosted-API backend can
   be added behind the same interface without touching experiment code.
   Consequence: results describe `qwen3:8b` on this runner. Recorded
   2026-09-16.
2. **USD price table is not implemented.** Local inference has a known zero
   marginal cost, recorded as `pricing_reference:
   local_inference_zero_marginal_cost`. The budget ledger bounds *tokens*
   rather than dollars. Any future paid backend stays `cost_unknown` until a
   price table exists — pinned by test.

## P1.1 Package skeleton — DONE

- [x] `pyproject.toml` with a `squelch` CLI; distribution name `squelch-skills`
- [x] uv lockfile; Ruff lint; pytest
- [x] Pydantic v2 schemas for all §4.1 entities, §4.2 events, §4.3 statuses
- [x] Canonical JSON hashing (sorted keys, no non-finite floats) + exact-byte
      file hashing
- [x] Scripted backend behind the backend protocol
- [x] `doctor`, `validate`, `plan`, `prereg`, `run`, `report`
- [x] CI: lint + keyless tests + offline demo; Docker sandbox as a separate
      job with an explicit daemon precondition
- [x] Apache-2.0; README stating what is and is not supported by measurement
- [ ] Public repository — local git only; pushing needs separate
      authorization (spec §14.10)
- [ ] Confirm `squelch-skills` is free on PyPI before any release

## P1.2 Skill ingestion — DONE

- [x] SKILL.md frontmatter parsing; name/description required
- [x] Per-file exact-byte hashes; package identity covers reference files
- [x] Symlink, size, and path-boundary validation
- [x] Unknown optional metadata preserved as data, never execution authority
- [x] Provenance surfaced from package metadata into every study and report

## P1.3 Task engine — DONE

- [x] Trusted evaluator: fresh directory, allowed-output filtering, grader
      never agent-visible; tamper / timeout / garbage-output / symlink tests
- [x] DockerEnv implementing the §5.3 container contract, with boundary tests
      (network off, read-only root, read-only mount) in a Docker-marked job
- [x] LocalEnv labeled non-isolating; its identity string marks every record
- [x] Eight task fixtures across four families, including harder v2 variants
- [x] Grader calibration tests: hidden reference solutions must pass, starters
      must not, graders must give partial signal (floor-effect guard)
- [ ] Pin the task image by digest rather than the `python:3.12-slim` tag
      before any confirmation-stage run

## P1.4 Live backend — DONE (Ollama)

- [x] Ollama backend behind the backend protocol; `/api/chat` tool-use format
      verified against the official documentation before implementation
- [x] Model tag pinned explicitly in config; reported model identity recorded
- [x] Usage capture (`prompt_eval_count` / `eval_count`)
- [x] Server reachability probe before any live dispatch; `doctor` reports it
- [x] Termination classification, including **output-cap truncation as
      `agent_limit`** — bug found in live pilot-001 artifacts and fixed
- [ ] A single hung request is bounded by the HTTP client timeout (600s)
      rather than preempted mid-request

## P1.5 Campaign planner — DONE

- [x] Token-budget ledger; `not_run_budget` persisted for unstarted runs
- [x] Crash-safe `--resume`; corrupt artifacts re-run rather than trusted;
      changed configs refused. Exercised for real when pilot-002 was
      interrupted at run 3 and resumed.
- [x] Preregistration required for live campaigns; hash bound into the study
      summary and printed in the report
- [x] `squelch plan` prints the grid and token envelope, contacting nothing

## P1.6 Constructed conflict — MACHINERY DONE, RESEARCH EXIT CRITERION NOT MET

- [x] Constructed pair authored: `modernize-thoroughly` (whole-file rewrites,
      extract helpers) vs `minimal-change` (no edits beyond the task, no new
      files), labeled constructed everywhere it appears
- [x] Four-condition grid with interaction contrasts and Wilson intervals;
      scripted demo shows the full pattern offline
- [ ] **The pair did not reproduce degradation against both singletons on the
      live model.** See docs/weekly/week-01.md. Per spec §6 the fixture must
      be redesigned until it does; that is the next bounded research task and
      it does not block the implementation.
- [ ] Baseline difficulty: 3 of 4 original tasks sat at 1.00 on qwen3:8b.
      Harder v2 variants are authored and grader-calibrated; measuring their
      live baselines is queued.

## P1.7 Report — DONE

- [x] Conditions side by side with the skills each exposed
- [x] Per-run assertions, usage, termination reason, file changes, and a
      `diff.patch` artifact
- [x] Four-condition interaction analysis with intervals and inline
      ceiling/floor caveats
- [x] Fixture provenance table; constructed fixtures flagged in the
      disclosure line
- [x] Verbosity and truncation diagnostics beside every success rate
- [x] Discloses backend, model, evidence stage, environment, N, status
      counts, config hash, preregistration hash, token totals, spend
- [x] HTML-escaped throughout; no remote assets, analytics, or CDN

## Measured cost (replaces the §4.5 placeholder for this backend)

From pilot-001, 48 live runs on qwen3:8b, local inference:

| Quantity | Value |
|---|---|
| Wall clock | ~61 s per run (~50 min for 48 runs) |
| Input tokens | ~1,700 per run (81,624 total) |
| Output tokens | ~1,640 per run (78,871 total) |
| USD | $0.00 — local inference, no marginal cost |

The binding constraint is wall clock, not money. A 48-run grid is about an
hour; plan phase-scale campaigns accordingly.
