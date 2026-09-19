# Squelch

> In radio, the *squelch* circuit suppresses unwanted noise on a channel so
> the signal comes through cleanly.

Agent skills that each work correctly alone can interfere when loaded
together. Squelch is an open-source experimental system that measures that
interference and tests whether rearranging how instructions are applied
suppresses it.

[![CI](https://github.com/kshesha1/Squelch/actions/workflows/ci.yml/badge.svg)](https://github.com/kshesha1/Squelch/actions/workflows/ci.yml)
[![Docs](https://github.com/kshesha1/Squelch/actions/workflows/docs.yml/badge.svg)](https://kshesha1.github.io/Squelch/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Documentation: https://kshesha1.github.io/Squelch/**

**Status: in progress. Phase 1 (instrumented laboratory) implemented.**

## What is supported by measurement, and what is not

The harness is built and tested. **No validated research finding exists yet.**
Specifically:

- Scripted results validate the program only — never a model-performance
  claim. They are labeled `evidence_stage: scripted` everywhere they appear.
- Live results so far are `screening`: small N, descriptive, on one local
  model and authored fixtures. They describe the Squelch runner, not coding
  agents in general.
- The constructed conflict pair has **not** been shown to degrade a live
  model. See [docs/weekly/week-01.md](docs/weekly/week-01.md) for what was
  measured and what failed.

## What the code does

- **Skill ingestion** with content-hashed package identity — editing a
  referenced file changes the package hash, so a decision made about the old
  version cannot silently apply to the new one.
- **A bounded tool-calling runner** behind a stage-scheduler abstraction. A
  stage plan of length *n* is the general case; Phase 1 uses n=1, and nothing
  special-cases that.
- **A constrained task sandbox** (Docker: no network, non-root, read-only
  root, dropped capabilities) plus a clearly-labeled non-isolating local
  fallback for offline development.
- **A trusted evaluator** that grades only declared outputs in a fresh
  directory with grader code the agent never sees.
- **A campaign planner** with interleaved condition order, a token-budget
  ledger, crash-safe resume, and preregistration binding.
- **Analysis and reporting**: Wilson intervals, four-condition interaction
  contrasts, verbosity/truncation diagnostics, and a self-contained HTML
  report with no remote assets.

## Backends

| Backend | Use | Cost |
|---|---|---|
| `scripted` | deterministic transcripts for offline tests and CI | free |
| `ollama` | live inference on a local model, no API key | $0 marginal |

The backend protocol is provider-neutral; a hosted-API backend can be added
behind the same interface without touching experiment code.

## Try the offline demo (no API key, no network, no Docker)

```bash
uv sync
uv run squelch doctor
uv run squelch run --config fixtures/campaigns/offline-demo.yaml --backend scripted --study-id demo
uv run squelch report demo --out report.html
```

For the four-condition machinery including the interaction analysis:

```bash
uv run squelch run --config fixtures/campaigns/conflict-demo.yaml --backend scripted --study-id conflict
uv run squelch report conflict --out conflict.html
```

Both are scripted by construction — they prove the pipeline can register a
difference, nothing more.

## Run a live local experiment

Requires [Ollama](https://ollama.com) running locally:

```bash
ollama serve                 # in another terminal
ollama pull qwen3:8b
uv run squelch plan --config fixtures/campaigns/conflict-pilot.yaml
uv run squelch run --config fixtures/campaigns/conflict-pilot.yaml --backend ollama --study-id pilot
```

`plan` never contacts a model. A live campaign refuses to start without a
preregistration file. If a run is interrupted, `--resume` reuses the
completed runs rather than repeating them.

## Reading results

`.squelch/studies/<study-id>/` holds:

- `study.json` — per-cell success counts, status counts, diagnostics
- `runs/<run-id>/result.json` — one run's grade, per-assertion
- `runs/<run-id>/events.jsonl` — ordered observable events
- `runs/<run-id>/diff.patch` — what the agent changed
- `runs/<run-id>/workspace/` — the final files

`squelch report <study-id>` renders all of it as one HTML page.

## Naming

The project, repository, import package, and CLI are all `squelch`. The PyPI
distribution name is `squelch-skills`, because bare `squelch` is already
taken by an unrelated SQL REPL package.

## Development

```bash
uv sync
uv run pytest -m "not docker"   # keyless, no network
uv run pytest -m docker         # container boundary tests; needs a daemon
uv run ruff check .
```

Container tests are a separate job: a missing Docker daemon must never
masquerade as a passed sandbox test.

## Documentation

The full documentation site is at **https://kshesha1.github.io/Squelch/**. It's built from the Markdown in [`docs/`](docs), so everything is readable here too.

- [spec.md](spec.md) — the full specification
- [docs/methodology.md](docs/methodology.md) — how claims are controlled
- [docs/results/pilot-001.md](docs/results/pilot-001.md) — the first live pilot: what was measured, and what failed
- [docs/weekly/week-01.md](docs/weekly/week-01.md) — the week 1 report
- [docs/decisions/](docs/decisions/) — implementation status and deviations

## License

Apache-2.0. Third-party skill and fixture licenses are tracked separately and
do not inherit the project license.
