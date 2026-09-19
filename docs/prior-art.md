---
title: Prior art
---

# Prior art

Squelch sits next to a lot of recent work on agent skills. This page lists what's closest, so the boundary is clear. Each entry below was fetched and checked on **2026-09-19**; descriptions paraphrase the papers' own abstracts. Squelch makes no claim about anyone's methodology beyond what's stated here, and none of it establishes that Squelch is first or that its methods work.

## Evaluating skills

| Work | What it does | Relevance |
|---|---|---|
| [Counterfactual Trace Auditing of LLM Agent Skills](https://arxiv.org/abs/2605.11946) (Zhou, Liu, Li, et al.) | Compares agent traces with and without skills to see how skills reshape behaviour, beyond pass rates | The same with/without idea Squelch builds on; Squelch adds multi-skill conditions |
| [SkillsBench](https://arxiv.org/abs/2602.12670) (Li, Liu, Chen, et al.) | A benchmark of 87 tasks across 8 domains measuring whether skills improve agent performance | Establishes that skill effects are measurable and vary; motivates careful calibration |
| **`claude plugin eval`** (Claude Code CLI) | Runs a plugin's eval cases and adds a no-plugin baseline arm, reporting the score delta | Answers "does this plugin beat no plugin?" Squelch asks the follow-on question of what happens when *two* skills share a turn |

## Context isolation vs. inline instructions

| Work | What it does | Relevance |
|---|---|---|
| [Subagents vs Agent Skills](https://arxiv.org/abs/2609.09233) (Piriyakulkij, Lawrence, Curth, et al.) | Compares invoking skill packages as dedicated subagents with fresh context windows against loading their instructions into the main agent's context | Closest to Squelch's Phase 3. Phase 3 plans a **matched-prompt inline arm** so context isolation and prompt framing are varied *separately* |

## Skill orchestration and lifecycle

| Work | What it does |
|---|---|
| [AgentSkillOS](https://arxiv.org/abs/2603.02176) (Li, Mu, Chen, et al.) | Organises skills into a capability tree and orchestrates them through pipelines at ecosystem scale |
| [SkillNet](https://arxiv.org/abs/2603.04448) (Liang, Zhong, Xu, et al.) | Open infrastructure to create, evaluate and organise skills |
| [Dynamic Agent Skills: A Lifecycle Survey](https://arxiv.org/abs/2607.10113) (Li) | Surveys how skill libraries evolve across 124 papers |
| [SLIM: Dynamic Skill Lifecycle Management](https://arxiv.org/abs/2605.10923) (Shen, Zhang, Zhao, et al.) | Treats the active skill set as an optimisation variable, retaining, removing and adding skills |
| [SkillWiki](https://arxiv.org/abs/2606.16523) (Huang, Ding, Liu, et al.) | Infrastructure for the full skill lifecycle including governance |
| [A Comprehensive Survey on Agent Skills](https://arxiv.org/abs/2605.07358) (Zhou, Shu, Su, et al.) | Taxonomy across representation, acquisition, retrieval and evolution |

Lifecycle management is an active, crowded area. **Squelch claims no novelty in lifecycle management as such.** Phase 5's contribution is narrower: decisions gated on measured composition and transfer evidence with declared margins, expiring automatically when identities change.

## Not the same thing

[Skill-Mix](https://arxiv.org/abs/2310.17567) (Yu, Kaur, Gupta, et al.) evaluates a language model's ability to *combine language skills in generated text*. Despite the surface similarity, it isn't about interference between loaded agent-skill packages. It's noted here to avoid naming confusion.

## Standards and engineering references

- [Agent Skills specification](https://agentskills.io/specification): the package format. Squelch's [compatibility notes](./reference/agent-skills-compat.md) document the supported subset.
- [Docker Engine security](https://docs.docker.com/engine/security/): informs the container threat model.
- [pytest](https://docs.pytest.org/en/stable/): trusted task checks and harness tests.
- [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html): a reminder to resample the correct unit; relevant to planned hierarchical bootstrapping.

## What Squelch adds, as design intent

Stated as intent, not as a finding:

- **Multi-skill conditions with the four-condition design**, so the pair's effect can be separated from either skill's.
- **Composition as an experimental variable** (ordering, phase separation, context isolation), with mandatory control arms.
- **Identity-based staleness**: decisions expire when a skill, model, or environment changes.
- **Honest instrumentation**: status separated from quality, replayable classification, and confounds surfaced beside every rate.
