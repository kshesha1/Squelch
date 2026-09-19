---
title: CLI reference
---

# CLI reference

```bash
uv run squelch --help
```

Results are read from and written to `.squelch/studies/` relative to the **current directory**.

## `squelch version`

Print the version.

## `squelch doctor`

Check the local environment: Python, Docker, Ollama, and the results directory. Missing Docker or Ollama is *reported*, not an error.

## `squelch validate --config FILE`

Parse a campaign config, load its task manifest and graders, load the skill inventory, and check that every condition references a skill that exists. Prints the planned run count, the available skills, the config hash, and the preregistration hash if there is one.

## `squelch plan --config FILE`

Print the run plan: campaign, backend, model, task/condition/repetition counts, per-run limits, a **conservative token envelope**, the budget, and the preregistration hash.

**Never contacts a model and never executes task code.**

## `squelch prereg --phase N --out FILE`

Write a preregistration template with the current git commit filled in. **Refuses to overwrite** an existing file. See [preregistration](../guides/preregistration.md).

## `squelch run`

```text
squelch run --config FILE [--backend scripted|ollama] [--study-id ID] [--resume]
```

| Option | Meaning |
|---|---|
| `--config FILE` | campaign YAML (required) |
| `--backend` | default `scripted`. **Must match the config's `backend`**; a mismatch is an error |
| `--study-id ID` | study name. Default: `<name>-<first 8 hex of config hash>` |
| `--resume` | reuse runs that completed identically; re-run missing or corrupt ones |

Prints the study id, status counts and the artifact path. For `ollama` it first probes the server and prints its version. If some runs were `not_run_budget`, it says the study is incomplete.

## `squelch replay STUDY_ID [--out-study ID]`

Re-derive each run's status and termination from its **recorded events** using the current rules, writing a **new** derived study (default `<STUDY_ID>-reanalyzed`). Contacts nothing, re-runs nothing, never modifies the source, and refuses when re-derivation wouldn't be faithful. See [replay](../architecture/analysis.md#replay-offline-re-analysis).

## `squelch report STUDY_ID [--out FILE]`

Render a self-contained HTML report (default `report.html`). See [reporting](../architecture/reporting.md).

## Exit codes

| Code | Meaning | Emitted today? |
|---|---|---|
| `0` | success | yes |
| `1` | completed comparison with a confirmed regression or block | reserved, not emitted |
| `2` | invalid configuration or execution, including any `invalid` run in a `run` | yes |
| `3` | insufficient evidence | reserved, not emitted |

## Not implemented yet

The spec's target CLI also names `init`, `compare`, `compose`, `generalize`, `lifecycle` and `export`. They are proposed, not implemented. See the [roadmap](../roadmap.md).
