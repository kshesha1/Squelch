# Offline demo bundle

Everything here was produced with **no API key, no network, and no Docker**,
using the deterministic `scripted` backend.

## Open these directly

- `conflict-report.html` — the four-condition design (none / A / B / A+B)
  with the interaction analysis, Wilson intervals, fixture provenance, and
  the verbosity/truncation diagnostics.
- `single-skill-report.html` — the simpler two-condition comparison.

## Regenerate them

```bash
uv run squelch run --config fixtures/campaigns/conflict-demo.yaml --backend scripted --study-id conflict-demo
uv run squelch report conflict-demo --out examples/demo/conflict-report.html
```

Takes a couple of seconds and costs nothing.

## Replay data

`replay/` holds a trimmed slice of the artifacts behind the report:

- `study.json` — the full study summary the report is rendered from
- `example-run-events.jsonl` — one run's ordered observable events, from
  `run_started` through skill exposure, tool calls, and grading
- `example-run-result.json` — that run's grade, assertion by assertion

Full artifacts for every run (workspaces, diffs, traces) regenerate locally
under `.squelch/studies/<study-id>/`.

## What this demonstrates, and what it does not

The scripted transcripts are written by hand. In the four-condition demo the
singleton conditions are scripted to succeed and the pair to fail, so the
report shows a clean interference pattern.

**That pattern is constructed, not measured.** It demonstrates that the
pipeline — workspace isolation, forced skill exposure, tool brokering,
trusted grading, interaction analysis, reporting — can detect and correctly
describe such a difference. It is not evidence that any real skill helps or
harms, and `modernize-thoroughly` is labeled in the report as a fixture
authored to collide by design.

Live results, when they exist, are labeled `screening` or `confirmation`
rather than `scripted`, and carry the model identity and preregistration
hash.
