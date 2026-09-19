---
title: Write a campaign
---

# Write a campaign

A campaign is a YAML recipe. This walks through building one; every key is listed in the [reference](../reference/campaign-config.md).

## A minimal four-condition live campaign

```yaml
schema_version: '1'
name: my-pilot
backend: ollama
preregistration: ../../docs/preregistration/my-pilot.yaml
skills_root: ../skills
graders_root: ../graders
model:
  id: qwen3:8b              # pin an explicit tag, never `latest`
  temperature: 0.2
  max_output_tokens: 2048
runner:
  max_model_calls: 12
  max_tool_calls: 30
  task_timeout_seconds: 600
dataset:
  manifest: ../tasks/development.yaml
conditions:
  - {id: none, skills: [],                 policy: shared}
  - {id: a,    skills: [skill-a],          policy: shared}
  - {id: b,    skills: [skill-b],          policy: shared}
  - {id: ab,   skills: [skill-a, skill-b], policy: shared}
repetitions: 3
schedule_seed: 42
budget:
  max_total_input_tokens: 4000000
  max_total_output_tokens: 800000
analysis:
  stage: screening
```

## Choosing the pieces

**Conditions.** Order matters inside `skills:`. `[skill-a, skill-b]` and `[skill-b, skill-a]` are different conditions. To study ordering, list both.

**Repetitions.** Three is a debugging default, not a confidence guarantee. To distinguish a real effect from noise you need more; the [pilot](../results/pilot-001.md) shows why.

**Schedule seed.** Drives the interleaving of condition order. Same seed, same manifest, same order.

**Limits.** Set `max_output_tokens` high enough that ordinary answers aren't cut off. A cut-off run is recorded as `agent_limit`, and if one condition is systematically more verbose it will hit the cap more often. Watch the [diagnostics table](../architecture/reporting.md).

**Timeout.** Checked between model calls. With a slow local model, be generous (600 s or more).

**Budget.** Optional token caps across the whole campaign. Unstarted runs become `not_run_budget`.

## An A/A trial

To estimate noise, run two conditions with **identical** skills under different labels:

```yaml
conditions:
  - {id: aa1, skills: [minimal-change], policy: shared}
  - {id: aa2, skills: [minimal-change], policy: shared}
```

Any gap between them is harness noise plus model variability. Use tasks that aren't at ceiling, or the trial tells you nothing: an A/A result of 6/6 vs 6/6 on saturated tasks is consistent with *any* noise level. See [`aa-trial.yaml`](https://github.com/kshesha1/Squelch/blob/main/fixtures/campaigns/aa-trial.yaml).

## A scripted campaign (for testing the harness)

```yaml
backend: scripted
scripted_transcripts: scripted/my-demo     # relative to the config file
analysis:
  stage: scripted
```

One transcript per task and condition at `scripted/my-demo/<task_id>/<condition_id>.json`. No preregistration is required for scripted campaigns.

## Validate, plan, run

```bash
uv run squelch validate --config fixtures/campaigns/my-pilot.yaml   # parse and check references
uv run squelch plan     --config fixtures/campaigns/my-pilot.yaml   # grid and token envelope; contacts nothing
uv run squelch run      --config fixtures/campaigns/my-pilot.yaml --backend ollama --study-id my-pilot
```

`--backend` must match the config's `backend`; a mismatch is an error, not an override.

## Changing a campaign later

A study is immutable and tied to its config's hash. If you change the config, **start a new study**. `--resume` refuses a changed config. This includes changing `max_output_tokens`, which alters what runs can do.
