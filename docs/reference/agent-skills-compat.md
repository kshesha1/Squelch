---
title: Agent Skills compatibility
---

# Agent Skills compatibility

Squelch's skill packages follow the shape of the [Agent Skills specification](https://agentskills.io/specification), which was consulted on 2026-09-19. Squelch implements a **supported subset** with its own loading behaviour, documented here independently.

:::warning Squelch is not a native Agent Skills host
It is a small, explicit runner that exposes its own skill-loading semantics. Results describe the Squelch runner, not every coding agent. It does not claim compatibility with every skill host.
:::

## Package shape

| Agent Skills spec | Squelch |
|---|---|
| A directory containing `SKILL.md` | same. The **directory name is the skill id** |
| Optional `scripts/`, `references/`, `assets/` | any files are accepted and **hashed**; none are exposed to the agent in Phase 1 |

## Frontmatter

| Field | Spec | Squelch |
|---|---|---|
| `name` | required; 1 to 64 chars, lowercase letters/digits/hyphens, must match the directory | required non-empty string. **Pattern and directory match are not enforced** |
| `description` | required; max 1024 chars | required non-empty string. **Length is not enforced** |
| `license` | optional | recorded on the snapshot |
| `compatibility` | optional | preserved as extra metadata |
| `metadata` | optional map of string to string | preserved as extra metadata |
| `allowed-tools` | optional, experimental | preserved as extra metadata; **never granted or acted on** |
| `source_url` | not in the spec | Squelch-specific; recorded on the snapshot |

Any other top-level key is preserved as `extra_metadata`: **data, never execution authority.**

:::note A known difference: `provenance`
Squelch reads a top-level `provenance:` key (for example `constructed-conflict-fixture`). The Agent Skills spec recommends custom keys live under `metadata:`. Squelch's fixtures use the top-level form; moving to `metadata.provenance` is a candidate change.
:::

## Loading behaviour

The spec describes **progressive disclosure**: metadata at startup, the body when a skill is activated, resources on demand.

| Mode | Status |
|---|---|
| **`forced`** | **Implemented.** The `SKILL.md` body (frontmatter stripped) is injected into the system prompt in declared order. Tests the effect of *exposure* |
| **`discovery`** | **Not implemented.** Would expose metadata and offer `load_skill` / `read_skill_resource` tools, logging catalog visibility, body exposure and reference exposure separately. Tests selection plus behaviour |

A discovered-but-unloaded skill must never be treated as body exposure, and a skill is never silently truncated: an oversized prompt fails planning.

## Identity

Package identity hashes **every file** in the package, including files the runner doesn't expose. Editing a reference file changes the hash even if `SKILL.md` is unchanged. That is stricter than the spec requires, and deliberate: a decision about a skill must not silently apply to a different version of it.

## Limits enforced by the loader

Symlinks are rejected, files over 1 MiB and packages over 8 MiB are rejected, and resource reads can't escape the package root.
