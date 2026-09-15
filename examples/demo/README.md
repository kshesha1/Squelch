# Offline demo

Runs the scripted campaign end to end — no API key, no network, no Docker
required — and renders the HTML report.

```bash
uv sync
uv run squelch run --config fixtures/campaigns/offline-demo.yaml --backend scripted --study-id demo
uv run squelch report demo --out examples/demo/report.html
```

What it demonstrates:

- 4 authored tasks x 2 conditions (`none`, `skill`) through the full
  pipeline: workspace reset, forced skill exposure, bounded tool loop,
  JSONL event trace, trusted evaluation, study summary, report.
- The `none` transcripts contain deliberate flaws (an unrelated scratch
  file, a half-fixed boundary, a dropped timeout argument, incomplete
  input handling); the `skill` transcripts are correct. The pipeline
  registers the difference.

**Provenance disclosure:** every behavior here is scripted by
construction. This validates the harness program only. It is not a model
result and says nothing about whether any skill helps or harms.
