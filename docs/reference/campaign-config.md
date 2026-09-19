---
title: Campaign config
---

# Campaign config reference

Every key `load_campaign()` reads. Relative paths resolve against **the config file's own directory**.

```yaml
schema_version: '1'
name: conflict-pilot
backend: ollama
preregistration: ../../docs/preregistration/phase-01.yaml
skills_root: ../skills
graders_root: ../graders
model:
  id: qwen3:8b
  host: http://localhost:11434
  temperature: 0.2
  max_output_tokens: 2048
runner:
  max_model_calls: 12
  max_tool_calls: 30
  task_timeout_seconds: 600
dataset:
  manifest: ../tasks/development.yaml
conditions:
  - {id: none, skills: [], policy: shared}
  - {id: ab, skills: [modernize-thoroughly, minimal-change], policy: shared}
repetitions: 3
schedule_seed: 42
budget:
  max_total_input_tokens: 4000000
  max_total_output_tokens: 800000
analysis:
  stage: screening
```

## Top level

| Key | Required | Default | Notes |
|---|---|---|---|
| `schema_version` | yes | none | must be `'1'` |
| `name` | yes | none | campaign name; part of the default study id |
| `backend` | yes | none | `scripted` or `ollama` |
| `scripted_transcripts` | scripted only | none | directory of `<task_id>/<condition_id>.json` |
| `skills_root` | no | `../skills` | directory of skill packages |
| `graders_root` | no | `../graders` | directory of `<task_id>/grade.py` |
| `preregistration` | **live: yes** | none | path to the preregistration file; its hash is recorded. Required unless `backend: scripted`. A declared-but-missing file is an error |
| `repetitions` | yes | none | integer |
| `schedule_seed` | yes | none | integer; drives condition-order shuffling |

## `model`

| Key | Default | Notes |
|---|---|---|
| `id` | none | **required for `ollama`**. Pin an explicit tag, never `latest` |
| `host` | `http://localhost:11434` | Ollama server |
| `temperature` | `0.0` | |
| `seed` | none | sampling seed. Improves repeatability; not a determinism claim |
| `max_output_tokens` | `2048` | **per model call**. A response cut off by it ends the run as `agent_limit` |

## `runner`

| Key | Default |
|---|---|
| `max_model_calls` | `12` |
| `max_tool_calls` | `30` |
| `task_timeout_seconds` | `180` (checked between model calls) |

## `dataset`

| Key | Notes |
|---|---|
| `manifest` | **required.** A YAML `{schema_version, tasks: [dirs]}`, paths relative to the manifest |

## `conditions`

A non-empty list. Each entry:

| Key | Default | Notes |
|---|---|---|
| `id` | required | unique within the campaign |
| `skills` | `[]` | ordered list of skill ids, exposed in this order |
| `policy` | `shared` | **only `shared` is accepted.** `phased` / `isolated` raise an error pointing at Phase 3 |

## `budget`

| Key | Notes |
|---|---|
| `max_total_input_tokens` | cumulative cap, checked **between runs** |
| `max_total_output_tokens` | cumulative cap, checked **between runs** |

Both optional. Unstarted runs become `not_run_budget`. There is no USD cap. See [campaigns](../architecture/campaigns.md#the-token-budget).

## `analysis`

| Key | Default | Notes |
|---|---|---|
| `stage` | `screening` | `scripted`, `screening`, `confirmation`, or `external_replication`; stamped on the study |

## Keys present in the shipped configs but not read

These appear in the example campaigns for parity with the spec and for human readers. **The code does not read them:**

- `runner.loading` (only `forced` exists),
- `dataset.split`,
- `analysis.primary_metric`,
- `analysis.minimum_useful_effect_pp`.

The spec's example also shows environment substitution (`id: ${SQUELCH_MODEL}`); that is **not supported**. Values are taken literally.
