---
title: Installation
---

# Installation

Squelch is a Python package managed with [uv](https://docs.astral.sh/uv/). It is **not yet on PyPI**; install from source.

:::note Naming
The project, repository, import package and CLI are all `squelch`. The planned PyPI *distribution* name is `squelch-skills`, because bare `squelch` is taken by an unrelated package. That name is not published yet.
:::

## Requirements

| Requirement | Needed for |
|---|---|
| Python 3.12 or newer | everything |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | environment and lockfile |
| [Ollama](https://ollama.com) | *optional*: live runs on a local model |
| Docker | *optional*: the container boundary tests |

The offline demo and the whole default test suite need **none** of the optional pieces: no API key, no network, no Docker.

## Install

```bash
git clone https://github.com/kshesha1/Squelch.git
cd Squelch
uv sync
```

## Check your setup

```bash
uv run squelch doctor
```

`doctor` reports the Python version, whether Docker's daemon is reachable, whether an Ollama server is reachable at `http://localhost:11434`, and where results will be written. A missing Docker or Ollama is reported, not treated as an error.

## Run the tests

```bash
uv run pytest -m "not docker"   # keyless, no network
uv run pytest -m docker         # container boundary tests; needs a Docker daemon
uv run ruff check .
```

Container tests are a separate marker on purpose: a missing Docker daemon must never masquerade as a passed sandbox test.

## Platforms

Developed on macOS (Apple Silicon). CI runs on Ubuntu. Windows is untested.

## Next

Run the [quickstart](./quickstart.md).
