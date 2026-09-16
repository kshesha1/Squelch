# Fixture skills

All skills here are **authored controls** written for this harness. They
establish pipeline behavior, not ecosystem prevalence.

- `minimal-change` — benign: change only what the task requires, no
  unrelated files.
- `edge-case-checklist` — benign: verify boundaries and invalid inputs
  before finishing.
- `modernize-thoroughly` — **constructed conflict fixture** (spec P1.6):
  its instructions are individually reasonable (consistent modernization,
  visible refactoring) but collide with `minimal-change` by design —
  one demands whole-file rewrites and helper modules, the other forbids
  edits beyond the task and any new files. The pair is the pipeline's
  positive control; every report that includes it must label it
  constructed.
