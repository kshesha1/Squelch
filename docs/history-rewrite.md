---
title: History rewrite (2026-09-19)
sidebar_label: History rewrite
---

# History rewrite on 2026-09-19

On 2026-09-19 the repository's history was rewritten **once**, for one reason: the commits carried a personal email address as author and committer. It was replaced with the GitHub identity `kshesha1` (the account's noreply address).

## What changed, and what did not

**Changed:** the author and committer name and email on 19 of the 20 commits. A commit hash covers that metadata, so every affected commit got a **new hash**.

**Unchanged**, and checked commit by commit before publishing:

- the file tree of every commit (each tree hash is identical),
- every author and committer date,
- every commit message,
- the order and shape of the history, including the merge with GitHub's initial commit.

GitHub's own signed initial commit (`0890fd6`) was left untouched, so it keeps its original hash and its signature.

## Why this matters for preregistration

[`docs/preregistration/phase-01.yaml`](https://github.com/kshesha1/Squelch/blob/main/docs/preregistration/phase-01.yaml) records `commit_hash: '3df7125'`, the implementation commit at the time the preregistration was written.

That file was **deliberately not edited**. Its content hash, `sha256:2069c94cfda3e0e965b176fb63872db847e42b9fd55f34d1cbe2bb03ad75b775`, is recorded in every pilot artifact and in the claims ledger, and it is still valid.

The commit it refers to is now **`319ff34`**. Since a tree hash covers the exact content, you can confirm it is the same snapshot:

```bash
git rev-parse 319ff34^{tree}     # 028b13d94ce889353983e39e1327edc04b5736a2
```

## Full mapping

| Original | Now | Tree | Commit |
|---|---|---|---|
| `e9d0911` | `e308f0e` | `72d864a20752` | Phase 1 (P1.1-P1.3): package skeleton, skill ingestion, task engine, scripted offline demo |
| `3df7125` | `319ff34` | `028b13d94ce8` | Phase 1 (P1.4-P1.7): Ollama live backend, planner with budget+resume, conflict fixture, full report  **(preregistration reference)** |
| `3db9ebf` | `167f0ce` | `a70c456d4108` | Pin phase-01 preregistration to implementation commit before live runs |
| `f4d6e43` | `b1e1d27` | `7d6606e4fed5` | Fix: classify token-cap-truncated responses as output-budget agent_limit |
| `953e492` | `e5c20a9` | `e1e88a8f4062` | Add per-condition verbosity/truncation diagnostics and the A/A trial config |
| `022db8c` | `faeef3a` | `2adfdbe03665` | Add harder v2 task variants and grader calibration tests |
| `540a8dc` | `e4a5b53` | `a9ab1536e206` | Add methodology doc and rewrite README for the current honest state |
| `f86b704` | `508c4ef` | `80fe16eb3954` | Disclose fixture provenance in every study summary and report |
| `5d672e3` | `f61ab14` | `8805ac094aa6` | Add redistributable offline example bundle |
| `38cd7ca` | `940f8f8` | `e92714b1432e` | Update Phase 1 checklist: ticket status, deviations, and measured cost |
| `27a626e` | `b4242bb` | `ffd55a62e28b` | Implement squelch replay: offline re-analysis of stored artifacts |
| `4c2e168` | `c93e4d4` | `4c6638bf57f3` | Week 01 write-up: two failed exit criteria, one instrument bug, no finding |
| `0890fd6` | `0890fd6` | `106a5f9b44a4` | Initial commit  (unchanged) |
| `e64b724` | `e2e9d82` | `f4c2c6dc422f` | Fix verbosity diagnostics: true median, and separate calls from per-call length |
| `83fcbfe` | `ed43c34` | `2081b4352a8e` | Publish redacted raw pilot data and correct two wrong numbers |
| `0473217` | `59a8c10` | `1f9cf1386d25` | Add comprehensive Docusaurus documentation site with GitHub Pages deployment |
| `7ec70a6` | `37c0da8` | `1f9cf1386d25` | Merge GitHub's initial commit into the project history |
| `f057594` | `36d9389` | `041570f1324e` | Docs: drop a speculative troubleshooting entry, fix a fixture miscount, record repo status |
| `994c219` | `e77c47c` | `2137a558c038` | Docs: note that Pages is enabled and the first deploy is pending |
| `2556d2c` | `9d6f3ce` | `3bc12e4a884b` | Docs: record that the site is live and verified |

## Caveats

- Old hashes may still appear in links, workflow-run pages, or third-party caches made before the rewrite.
- The rewrite was done with `git filter-branch` restricted to identity fields; no file content, message, or date was touched.
