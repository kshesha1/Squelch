---
title: Data contracts
---

# Data contracts

Everything Squelch persists is a validated record. `schemas.py` defines them with Pydantic v2 in strict mode (unknown fields are rejected), and `hashing.py` defines how identity works.

## Hashing

Two regimes:

- **Structured records** hash as *canonical JSON*: UTF-8, sorted keys, compact separators, no non-finite floats and no non-string keys (both raise).
- **Files** hash as their **exact bytes**.

All hashes are `sha256:<hex>`. `hash_tree()` hashes a directory as a mapping of relative POSIX path to file hash, and **refuses symlinks**, so a tree's identity can't depend on content outside it.

Identity is used everywhere: a skill package hash covers every file in the package (a reference-file edit changes it), a task binds prompt, starter-tree, grader and environment, a campaign has a config hash, and a preregistration has a file hash.

## Core records

| Record | What it holds |
|---|---|
| `SkillSnapshot` | skill id, package hash, name, description, file-to-hash map, source URL and license if declared, extra metadata |
| `TaskSpec` | task id, family id, split, prompt / starter-tree / grader hashes, environment identity, allowed outputs, public checks, limits |
| `ModelSpec` | provider, requested model id, parameters, cost status and pricing reference |
| `CollectionSnapshot` | ordered skill hashes, composition policy, loading mode, system-prompt hash, tool-schema hash, runner version |
| `StageSpec` | stage id, forced skill ids in order, limits |
| `RunSpec` | one planned run: task, collection, model, repetition, seed, stage plan, study id |
| `StageResult` | per-stage worker id, exposed skills, model and tool calls, usage, termination reason |
| `RunResult` | status, `task_success`, assertions, usage, spend status, artifact hashes, trace path, termination reason, changed files, stage results, error |
| `Event` | one line of the event log (below) |

`Comparison` and `Preregistration` models exist in `schemas.py` for later phases; in Phase 1 the preregistration is a hashed YAML file and comparisons are computed at report time.

Every record carries `schema_version`. Campaign configs, task fixtures and manifests, and scripted transcripts reject an unsupported version explicitly (`SchemaVersionError`). Records read back from a study (results, events) are validated against their Pydantic model but are **not version-gated yet**.

## Events

Each line of `events.jsonl` is one event:

```json
{
  "schema_version": "1",
  "event_id": "demo-r0001:0007",
  "run_id": "demo-r0001",
  "stage_id": "implement",
  "sequence": 7,
  "agent_id": "worker-1",
  "phase": "run",
  "type": "tool_completed",
  "payload": {"name": "write_file", "is_error": false, "output_chars": 28},
  "timestamp": "2026-09-17T14:59:44.561Z"
}
```

Event types and their payloads:

| Type | Payload |
|---|---|
| `run_started` | `condition_id`, `task_id`, `repetition`, `backend`, `environment`, `stage_count` |
| `stage_started` | `stage_id`, `worker_id` |
| `skill_loaded` | `skill_id`, `package_hash`, `file`, `content_hash`, `reason` (`forced`) |
| `model_request` | `call_index`, `message_count` |
| `model_response` | `stop_reason`, `tool_call_count`, `usage` |
| `tool_requested` | `tool_call_id`, `name`, `input` |
| `tool_completed` | `tool_call_id`, `name`, `is_error`, `output_chars` |
| `file_written` | `path` |
| `limit_reached` | `limit`, `value`, and for the output cap `stop_reason`, `had_tool_calls` |
| `stage_finished` | `stage_id`, `termination_reason`, `model_calls`, `tool_calls` |
| `evaluation_completed` | `task_success`, `assertions` |
| `run_finished` | `status`, `task_success` |
| `run_error` | `error`, `kind` (`backend`, `interrupt`, `evaluator`) |

`catalog_exposed` and `handoff_created` are reserved for discovery mode and multi-stage handoffs and are **not emitted yet**.

Sequence numbers are strictly increasing per run. Squelch stores observable calls, exposed instructions, file changes and outcomes. It does **not** require, infer or fabricate private reasoning traces.

## Where things live

Results are written under `.squelch/` (git-ignored). Only explicitly selected, redacted bundles are published under `examples/`. The layout is in [artifacts](../reference/artifacts.md).
