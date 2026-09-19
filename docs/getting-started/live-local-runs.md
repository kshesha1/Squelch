---
title: Live local runs (Ollama)
---

# Live local runs with Ollama

Squelch's live backend talks to a local [Ollama](https://ollama.com) server. There is **no API key and no cloud spend**: the model runs on your machine, and each run costs $0 in marginal terms.

:::info Why Ollama and not a hosted API?
The spec's first live backend was a hosted API. This project deliberately chose local inference instead. The backend interface is provider-neutral, so a hosted backend can be added later without touching experiment code. See [backends](../architecture/backends.md).
:::

## 1. Install and start Ollama

```bash
brew install ollama          # or download from https://ollama.com
ollama serve                 # leave running in another terminal
ollama pull qwen3:8b         # ~5 GB
```

Confirm Squelch can see it:

```bash
uv run squelch doctor
# ollama: server 0.34.0 reachable at http://localhost:11434 (live local runs usable)
```

## 2. Plan first (contacts nothing)

```bash
uv run squelch plan --config fixtures/campaigns/conflict-pilot.yaml
```

`plan` prints the grid (tasks x conditions x repetitions), per-run limits, a conservative token envelope, and the preregistration hash. It never contacts a model or executes task code.

## 3. Preregistration is required

A live campaign **refuses to start** without a `preregistration:` file, and its hash is recorded in every result. The pilot campaign points at [`docs/preregistration/phase-01.yaml`](https://github.com/kshesha1/Squelch/blob/main/docs/preregistration/phase-01.yaml). To start your own, see [preregistration](../guides/preregistration.md).

## 4. Run

```bash
uv run squelch run \
  --config fixtures/campaigns/conflict-pilot.yaml \
  --backend ollama \
  --study-id my-pilot
```

That is 4 tasks x 4 conditions x 3 repetitions = 48 runs. Budget **hours, not minutes**: the first pilot took about 3 hours (median 94 s, mean 223 s per run) on Apple Silicon with an 8B model, and cost $0.

If the process is interrupted, resume rather than restart:

```bash
uv run squelch run --config fixtures/campaigns/conflict-pilot.yaml \
  --backend ollama --study-id my-pilot --resume
```

`--resume` reuses runs that completed *identically* and re-runs anything missing or corrupt. It refuses if the config changed: a changed manifest needs a new study.

## 5. Read it

```bash
uv run squelch report my-pilot --out pilot.html
```

## Memory is the real constraint

:::warning Keep RAM free
On the reference machine the 8B model held ~5.6 GB resident. When free memory dropped to a few hundred MB with several GB in swap, single model calls stretched from about **20 seconds to 14 minutes**, because the model was being paged in and out. A local lab is gated on free RAM, not money.

- Close memory-hungry apps before a long campaign.
- Don't run the test suite or other heavy work while a campaign is running.
- If calls suddenly slow down, check swap before suspecting the code.
:::

## Pin the model

Campaign configs pin an explicit tag (`qwen3:8b`), never `latest`. Squelch records both the requested and the *reported* model identity for every response, so a silently substituted model shows up in the artifacts.

## Stop the server when you're done

```bash
pkill -f "ollama serve"
```

## Next

[Troubleshooting](../guides/troubleshooting.md) covers the failure modes we've actually hit.
