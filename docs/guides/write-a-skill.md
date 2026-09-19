---
title: Write a skill
---

# Write a skill fixture

A skill is a directory under `fixtures/skills/`. The **directory name is the skill id** used in campaigns.

```text
fixtures/skills/minimal-change/
  SKILL.md            # required
  references/...      # optional extra files
```

## `SKILL.md`

YAML frontmatter, then Markdown instructions:

```markdown
---
name: minimal-change
description: Keep edits minimal - change only what the task requires and never create unrelated files.
license: Apache-2.0
---

# Minimal change discipline

When editing a workspace:

1. Read the existing files before writing anything.
2. Change only the lines the task requires.
...
```

| Key | Required | Notes |
|---|---|---|
| `name` | yes | non-empty string |
| `description` | yes | non-empty string |
| `license` | no | recorded on the snapshot |
| `source_url` | no | Squelch-specific; recorded on the snapshot |
| anything else | no | preserved as `extra_metadata`: **data, never execution authority** |

`provenance` is one such extra key. A skill can declare `provenance: constructed-conflict-fixture`, and Squelch reads it into every study summary and report. A skill that doesn't declare it is reported as `undeclared`, **never assumed benign**.

## What the loader checks

`load_skill_package()` (`skills/loader.py`) rejects:

- a missing `SKILL.md`, missing or unterminated frontmatter, or frontmatter that isn't a YAML mapping,
- a missing or empty `name` or `description`,
- any **symlink** in the package (files or directories),
- any file over 1 MiB, or a package over 8 MiB total,
- resource reads that are absolute or escape the package root.

## Identity: why editing a skill matters

Every file's exact bytes are hashed, and the **package hash** is the hash of that file-to-hash map. So:

- editing `SKILL.md` changes the package hash,
- editing a *referenced* file changes it too, **even if `SKILL.md` is untouched**,
- results record the hashes of the skills they used.

```bash
uv run python - <<'EOF'
from squelch.skills import load_skill_package
p = load_skill_package("fixtures/skills/minimal-change")
print(p.snapshot.package_hash)
print(p.snapshot.files)
EOF
```

:::tip A concrete example from this repo
The two benign skills, `minimal-change` and `edge-case-checklist`, don't declare a `provenance`. Adding one would be a one-line change, but it would change their package hashes and detach the published pilot results from the files that produced them. So they're left as they were, and reports show them as `undeclared`. That is the staleness problem this whole project is about, in miniature.
:::

## What the agent actually sees

In `forced` mode, the body of `SKILL.md` (everything after the frontmatter) is appended to the system prompt, wrapped as `<skill name='...'> ... </skill>`, in the order the condition lists the skills. Reference files are **not** shown to the agent in Phase 1. See [Agent Skills compatibility](../reference/agent-skills-compat.md).

## Writing a good test skill

- Make instructions **observable**. "Keep changes minimal" can be graded by whether unrelated files appeared; "write elegant code" can't.
- If you're building a *conflict* fixture, draw it from genuinely reasonable instructions that collide, not direct contradictions, and **label it** with `provenance`. See the [fixture inventory](../reference/fixtures.md).
- Keep it short. Longer instructions make the model more verbose, which is itself a [confound](../concepts/experiment-design.md#confounds-the-harness-watches-for).

## Use it

Add its id to a condition in a [campaign](./write-a-campaign.md):

```yaml
conditions:
  - {id: none, skills: [], policy: shared}
  - {id: a,    skills: [my-new-skill], policy: shared}
```
