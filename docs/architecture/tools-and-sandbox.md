---
title: Tools and sandbox
---

# Tools and sandbox

## The four tools

The agent gets exactly four tools, defined in `TOOL_SCHEMAS` (`runner/tools.py`):

| Tool | Input | Does |
|---|---|---|
| `list_files` | none | Lists regular files in the workspace, recursively |
| `read_file` | `path` | Reads a UTF-8 text file |
| `write_file` | `path`, `content` | Writes a UTF-8 text file, creating parent directories |
| `run_checks` | `check_id` | Runs one **public** check declared by the task |

There is no shell tool. `run_checks` takes an *id*, never a command line, so the agent can only run checks the task author allowlisted.

## The `ToolBroker` is the bouncer

Every call goes through `ToolBroker`, which enforces:

- **Relative paths only.** Empty paths, absolute paths, and any `..` component are rejected.
- **No symlink traversal.** Each existing ancestor is checked, so a symlink pointing outside the workspace can't be used to read or write outside it.
- **Containment.** The resolved parent must be inside the workspace.
- **Size limits.** Reads and writes over `max_file_bytes` (262,144 by default) are rejected.
- **UTF-8 only.** A non-UTF-8 file is an error.
- **Public checks only.** A non-public check id is treated as unknown.

Every rejection raises a `ToolError`, which is returned to the model as an error result; it does not end the run. These rules are exercised in [`tests/unit/test_tool_broker.py`](https://github.com/kshesha1/Squelch/blob/main/tests/unit/test_tool_broker.py), including `../escape.txt`, `/etc/passwd`, and a symlink pointing outside.

## Where commands run: `LocalEnv` and `DockerEnv`

Both implement the same tiny interface, `run(cmd, workspace, timeout_seconds, readonly)`, and each reports an **identity string** that is stamped into every result.

### `LocalEnv`

Runs the command as a normal subprocess on your machine with a minimal environment (`PATH=os.defpath`, `HOME` set to the workspace, deterministic hash seed). A command of `python` resolves to the interpreter running Squelch. Identity looks like `local:python-3.13.14:darwin`.

:::danger LocalEnv is not a security boundary
`LocalEnv` has **no network isolation and no filesystem isolation**. During `run_checks` and during grading, code the *model wrote* executes on your machine with your privileges.

Use it only with the authored, benign fixtures in this repository and a model you trust. Never point it at untrusted tasks or skills. Squelch supports only authored or manually reviewed fixtures.
:::

### `DockerEnv`

Runs each command in a constrained container:

| Flag | Effect |
|---|---|
| `--network none` | no network |
| `--user 1000:1000` | non-root |
| `--cap-drop ALL`, `--security-opt no-new-privileges` | no capabilities, no privilege gain |
| `--read-only` | read-only root filesystem |
| `--memory 512m --cpus 1 --pids-limit 128` | resource limits |
| `--tmpfs /tmp:rw,noexec,nosuid,size=64m` | bounded scratch space |
| `-v <workspace>:/workspace:rw\|ro` | the only writable mount, or read-only |

Identity looks like `docker:python:3.12-slim`. Four container-boundary tests (network off, read-only root, read-only mount, basic execution) live in `tests/integration/test_docker_env.py` behind the `docker` marker and run as a **separate CI job** that first verifies the daemon is actually available.

:::warning Docker is implemented and tested but not yet wired into `squelch run`
Campaigns currently always use `LocalEnv`. Every live result so far, including the pilot, ran in `LocalEnv`. Selecting `DockerEnv` from the CLI is on the [roadmap](../roadmap.md#known-gaps-in-whats-built). Until then, treat live results as produced in a non-isolating environment; the identity string in each artifact says so.
:::

Containers are a scoped execution boundary, not a certification for hostile code.
