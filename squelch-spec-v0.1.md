# Squelch — Specification

**Version 0.1 · 2026-09-15 · Status: ready to implement Phase 1**

> In radio, the *squelch* circuit suppresses unwanted noise on a channel so the signal comes through cleanly. Agent skills that each work correctly alone can interfere when loaded together. This project measures that interference and tests whether rearranging how instructions are applied suppresses it.

---

## 1. Purpose

Squelch is an open-source experimental system for evolving agent skill collections. It discovers when skills help, interfere, or become unnecessary, and tests whether changing how their instructions are applied improves outcomes.

The long-term question: **can an agent maintain useful expertise without accumulating conflicting or obsolete instructions?**

Five phases build a credible, inspectable slice of that. Each phase produces a runnable release, a measured experiment, a visual artifact, and one public progress write-up. The goals are learning, practical usefulness, and technical credibility. Revenue is not a requirement.

This is a five-week target, not a promise of five weeks of research success. Plan roughly 15–25 focused hours per phase. Ship the bounded increment and report uncertainty rather than expanding scope to force a positive result.

### 1.1 Primary hypothesis

**When two individually useful skills degrade agent behavior in combination, changing how their instructions are applied — ordering, phase separation, or context isolation — can preserve more of their individual benefit than loading both together or removing one.**

This is a hypothesis to evaluate, not an established novelty claim.

### 1.2 Secondary hypothesis

**A composition decision is conditional on task family, model, and skill version, and becomes stale when those change.**

### 1.3 Nearest prior art and the specific gap

- **CTA** [S4] audits paired with-skill / without-skill traces for a *single* skill. It never runs two skills together, uses one repetition per condition, and reports no confidence intervals.
- **Subagents vs Agent Skills** [S13] compares inline vs isolated execution — closest to Phase 3 — but varies context isolation and prompt framing together, with no matched-prompt inline arm, no intervals, and results filtered to 64 of 87 tasks. **Phase 3 is the controlled version of this comparison.**
- **SkillsBench** [S14] names skill composition (synergy vs. interference) as explicit future work and proposes length-matched controls.
- Lifecycle work [S6, S7, S8, S15, S16] is active and crowded. Phase 5 claims no novelty in lifecycle management as such; its contribution is that decisions are gated on measured composition and transfer evidence with declared margins, and expire automatically when identities change.

### 1.4 Users

- Skill authors checking whether a change helps its target workflow and harms neighboring ones.
- Developers maintaining a small skill collection for a coding agent.
- Researchers comparing instruction composition strategies with inspectable experiments.
- The author, learning agent engineering and publishing reproducible findings.

### 1.5 Product questions

1. Does a skill help on these tasks in this environment?
2. Does its effect change when another skill is present?
3. Can ordering, phase separation, or isolated contexts improve the combination?
4. Does that finding survive unseen tasks, a different model, or a skill edit?
5. Should a candidate configuration be admitted, deferred, or reverted?

---

## 2. Phase map

| Phase / week | Increment | Research question | Public artifact |
|---|---|---|---|
| 1 | Instrumented laboratory + reproducible constructed conflict | What changes when a skill is exposed, and can we make a conflict appear on demand? | Single-skill comparison, trace viewer, first conflict demo |
| 2 | Contextual interaction map | Does combination harm occur with skills not designed to conflict? | Four-condition heatmap and evidence card |
| 3 | **Composition experiment engine (core)** | Can changing how skills are applied preserve their benefits? | Shared vs. phased vs. isolated, with control arms |
| 4 | Generalization and staleness harness | Does the winning arrangement survive new tasks, a new model, a skill edit? | Holds/breaks matrix |
| 5 | Lifecycle workbench | Can a collection respond sensibly to change? | Candidate → experiment → decision → rollback timeline |

Phase 3 is the centerpiece. Phases 1–2 make it trustworthy; Phases 4–5 make it durable and actionable. **If time runs short, protect Phase 3's control arms before anything else.**

No phase requires a new agent framework, hosted service, marketplace, model training, or automatic publishing. All five run locally, with paid inference explicitly enabled by the operator.

---

## 3. Engineering decisions

### 3.1 Stack

- Python 3.12+; `uv` for environment and lockfile; `pyproject.toml` with a `squelch` CLI entry point.
- **Naming:** the project, repository, import package, and CLI are all `squelch`. The PyPI *distribution* name is `squelch-skills`, because bare `squelch` is already taken by an unrelated SQL REPL package. Install is `pip install squelch-skills`; import and invocation are both `squelch`. Confirm both names are still free before the first release.
- Typer for CLI, Pydantic v2 for strict schemas, PyYAML safe parsing for configuration.
- SQLite index plus immutable JSON/JSONL artifacts. SQLite is rebuildable; artifacts are authoritative.
- NumPy/SciPy for statistics; pytest for harness and evaluator tests; Ruff for formatting and linting.
- Jinja2-generated, self-contained HTML reports with local JavaScript and SVG. No frontend build system, remote analytics, or CDN dependency.
- A small explicit tool-calling runner. First live backend: Anthropic client tools via the official SDK. Also a scripted backend for free, deterministic harness tests.
- The exact model ID and SDK version are selected and recorded at implementation time. Never silently resolve `latest`, substitute a model, or bake unverified prices into results.
- Docker-based task execution. The host coordinates inference; generated code executes only in constrained task containers.
- License: Apache-2.0. Third-party skill and fixture licenses are tracked separately and do not inherit the project license.

The runner deliberately exposes its skill-loading semantics. It is not an emulation of every commercial coding agent. Results describe the Squelch runner until an independently tested native-runner adapter exists.

### 3.2 Architecture

```text
CLI / campaign manifest
          |
          v
Planner -----> budget ledger -----> immutable run queue
                                      |
                                      v
                       Composition policy -> Stage scheduler
                              |                    |
                       Worker (1..n)          Tool broker
                         |                         |
                   Model backend            Task container
                              |
                              v
                     Event log + artifacts
                              |
                 Trusted evaluator (fresh container)
                              |
                 Comparisons / interaction evidence
                              |
               HTML report + lifecycle decision record
```

**The stage scheduler and worker abstraction exist from Phase 1**, where every run is a single-stage, single-worker trial. Phase 3 adds multi-stage policies without restructuring the runner. Do not inline single-stage assumptions.

The lifecycle module (Phase 5) selects collection configurations from evaluated candidates. It cannot turn incomplete evidence into a pass.

### 3.3 Repository layout

```text
squelch/
  pyproject.toml
  uv.lock
  README.md
  LICENSE
  spec.md
  src/squelch/
    cli.py
    schemas.py
    hashing.py
    skills/          # package parser, content snapshots, loader
    backends/        # scripted.py, anthropic.py, protocol.py
    runner/          # stage scheduler, worker loop, tool broker, limits, skill exposure
    sandbox/         # task containers and trusted evaluator
    experiments/     # planner, scheduler, budget, identity, preregistration
    evaluation/      # task assertions, aggregation, validity
    analysis/        # effects, intervals, multiplicity, diagnostics
    composition/     # shared, phased, isolated policies        [Phase 3]
    generalization/  # transfer axes, staleness detection       [Phase 4]
    lifecycle/       # snapshots, change detection, decisions    [Phase 5]
    reporting/       # templates and bundled assets
  fixtures/
    skills/          # authored benign skill packages + constructed conflict pair
    tasks/           # prompts, starter files, task manifests
    graders/         # trusted acceptance checks; never agent-visible
    campaigns/
  tests/
    unit/
    integration/
    statistical/
    fixtures/        # scripted transcripts and expected outcomes
  examples/
    demo/            # small redistributable report and replay data
  docs/
    methodology.md
    prior-art.md
    decisions/
    preregistration/ # phase-01.yaml ... phase-05.yaml (hashed, committed before live runs)
    weekly/          # week-01.md ... week-05.md and evidence manifests
  .github/workflows/ci.yml
```

Local results go in `.squelch/`, git-ignored. Publish only explicitly selected, redacted bundles under `examples/` or release assets. No provider secrets or private repositories in fixtures.

**The repository is public from Phase 1.** The README states that the project is in progress and which claims are supported by measurement.

---

## 4. Data contracts

All persisted records carry `schema_version`, stable IDs, and UTC timestamps. Validate unknown enum values and incompatible schema versions explicitly. Use canonical UTF-8 JSON with sorted keys and no non-finite floats for hashing; source file hashes use exact bytes. Reject symlinks escaping a skill or task root. Cover schema migrations in tests.

### 4.1 Core entities

| Entity | Required fields and semantics |
|---|---|
| `SkillSnapshot` | `skill_id`, `package_hash`, parsed name/description, relative file-to-hash map, source URL/license if imported; a reference-file edit changes package identity |
| `TaskSpec` | `task_id`, `family_id`, `split`, prompt hash, starter-tree hash, environment image digest, grader hash, allowed outputs, resource limits |
| `ModelSpec` | provider, requested model ID, reported model ID when available, parameters, SDK version, pricing reference/version or `cost_unknown` |
| `CollectionSnapshot` | ordered skill hashes, composition policy hash, loading mode, system-prompt hash, tool schema hash, runner version |
| `RunSpec` | task, collection, model, repetition index, schedule seed, condition ID, stage plan, limits, study ID |
| `StageResult` | stage ID, worker ID, exposed skills, model calls, tokens, handoff produced, termination reason |
| `RunResult` | status, assertion outcomes, metric values, usage, spend status, artifact hashes, trace path, termination reason, ordered `StageResult` list |
| `Comparison` | exact baseline/candidate IDs, estimand, analysis unit, effect estimate, uncertainty method, interval, exclusions, evidence stage, preregistration hash |
| `InteractionEvidence` | task family and environment context, tested skill group/order, four-condition IDs, effect, uncertainty, diagnostic references; never a universal compatibility claim |
| `Preregistration` | phase ID, declared hypotheses, primary endpoint, minimum useful effect, planned N and rationale, analysis method, exclusion rules, commit hash, timestamp |
| `DecisionRecord` | candidate/current hashes, policy hash, relevant comparisons, scope, verdict, rationale codes, timestamp, supersedes/rollback target |

Distinguish `evidence_stage: scripted | screening | confirmation | external_replication`. A scripted result validates the program, never a model-performance claim.

### 4.2 Events

JSONL event fields:

```json
{
  "schema_version": "1",
  "event_id": "run-001:0007",
  "run_id": "run-001",
  "stage_id": "implement",
  "sequence": 7,
  "agent_id": "worker-1",
  "phase": "implementation",
  "type": "skill_loaded",
  "payload": {
    "skill_id": "minimal-change",
    "package_hash": "sha256:...",
    "file": "SKILL.md",
    "content_hash": "sha256:...",
    "reason": "explicit_load_tool"
  }
}
```

Other event types: `run_started`, `stage_started`, `stage_finished`, `catalog_exposed`, `model_request`, `model_response`, `tool_requested`, `tool_completed`, `file_written`, `handoff_created`, `limit_reached`, `evaluation_completed`, `run_finished`, `run_error`.

Store provider request/response bodies locally after credential redaction, linked as artifacts when large. Record tool-call IDs and structured results. Do not require, infer, or fabricate private reasoning traces. Diagnostics use observable calls, exposed instructions, file changes, and outcomes.

### 4.3 Execution status is separate from quality

- `completed` — agent stopped normally; may pass or fail the task.
- `agent_limit` — model loop exhausted declared calls/time/output budget; counts as non-success for the task endpoint.
- `invalid` — sandbox failure, provider outage after retry allowance, corrupt fixture, or evaluator failure; not ordinary agent failure.
- `not_run_budget` — never started because campaign funds were insufficient.
- `interrupted` — operator interruption or host crash; preserve partial artifacts, report separately.

Always publish status counts and valid denominators. A provider refusal or invalid tool choice is agent behavior unless the request was malformed by the harness. Never silently replace an inconvenient result.

### 4.4 CLI contract

Target interface, not existing functionality:

```bash
squelch init ./my-study
squelch doctor
squelch validate --config campaigns/baseline.yaml
squelch prereg --phase 1 --out docs/preregistration/phase-01.yaml
squelch plan --config campaigns/baseline.yaml
squelch run --config campaigns/baseline.yaml --backend scripted
squelch run --config campaigns/baseline.yaml --allow-paid --max-usd 10
squelch report STUDY_ID --out report.html
squelch replay RUN_ID
squelch compare BASELINE_ID CANDIDATE_ID
squelch compose --study STUDY_ID --pair A,B --policies shared,phased,isolated
squelch generalize --study STUDY_ID --axis tasks|model|skill-version
squelch lifecycle evaluate --current CURRENT --candidate CANDIDATE --policy policy.yaml
squelch lifecycle promote DECISION_ID
squelch lifecycle rollback --to SNAPSHOT_ID
squelch export STUDY_ID --public --out ./release-bundle
```

`replay` is offline artifact playback and re-analysis; it does not rerun the agent or establish model determinism. `run --resume STUDY_ID` may reuse completed *identical planned run IDs* but must never pool cached model responses as independent trials. Changed manifests require new studies.

Exit codes: `0` meets declared criteria · `1` completed comparison with confirmed regression/block · `2` invalid configuration or execution · `3` insufficient evidence. Reports remain available for all statuses. `plan` never contacts a model or executes task code.

### 4.5 Campaign example

```yaml
schema_version: '1'
name: phase-02-interactions
backend: anthropic
preregistration: docs/preregistration/phase-02.yaml
model:
  id: ${SQUELCH_MODEL}
  max_output_tokens: 2048
runner:
  loading: forced
  max_model_calls: 12
  max_tool_calls: 30
  task_timeout_seconds: 180
  concurrency: 1
dataset:
  manifest: fixtures/tasks/development.yaml
  split: development
conditions:
  - {id: none, skills: [], policy: shared}
  - {id: a, skills: [migration-guide], policy: shared}
  - {id: b, skills: [minimal-change], policy: shared}
  - {id: ab, skills: [migration-guide, minimal-change], policy: shared}
repetitions: 3
schedule_seed: 42
budget:
  max_usd: 10
  max_total_input_tokens: 250000
  max_total_output_tokens: 60000
analysis:
  stage: screening
  primary_metric: task_success
  minimum_useful_effect_pp: 10
```

These are engineering defaults, not statements of statistical power or promised cost. USD accounting requires a configured price table covering relevant cached-input categories. Without valid prices, paid runs require explicit acknowledgement of unknown spend and enforce token/call limits; they cannot claim a hard dollar cap.

**Per-phase budget guidance** — replace with real numbers after Phase 1 measures actual per-run cost:

| Phase | Shape | Starting cap |
|---|---|---|
| 1 | ~24–48 runs, single stage | $10 |
| 2 | 2 predeclared pairs screened; full grid optional | $15–25 |
| 3 | pairs × policies × control arms; `isolated` ≈ 3 workers/trial | $40–60; measure one policy before planning the rest |
| 4 | best policy re-run across 3 transfer axes | $30–50; a second model doubles per-cell cost |
| 5 | mostly replay of existing evidence + one live case | $10–20 |

---

## 5. Experiment integrity and safety

### 5.1 Preregistration

Before any live campaign in a phase, commit `docs/preregistration/phase-NN.yaml` with declared hypotheses, primary endpoint, minimum practically useful effect, planned sample size and its rationale, analysis method, and exclusion rules. Its hash is recorded in every resulting `Comparison`. Any analysis not in the file is labeled exploratory in reports and posts.

### 5.2 Skill-loading semantics

Two clearly distinguished modes:

1. `forced` — inject exactly the prescribed skill content and order. Tests effects conditional on exposure.
2. `discovery` — expose metadata for the configured catalog; allow explicit `load_skill` and `read_skill_resource` tools. Log actual exposure separately from availability. Tests selection plus downstream behavior.

Phase 1 is forced only; Phase 2 adds discovery. Never treat a discovered-but-unloaded skill as body exposure. Never silently truncate a skill: fail planning if the declared input envelope cannot fit, or use a separately named truncation condition.

The package format follows the Agent Skills specification [S1]. Record the retrieval date and supported subset. Do not describe a custom prompt injector as native compatibility with every skill host.

### 5.3 Tools and task sandbox

Minimal tools: `list_files`, `read_file`, `write_file`, `run_checks`, `load_skill`, `read_skill_resource`. Structured schemas, explicit size limits, normalized paths.

- File operations execute through the container boundary and stay inside `/workspace`; reject absolute escapes, `..`, symlink traversal, and oversized payloads.
- `run_checks` takes an allowlisted check ID, never an arbitrary host shell command. Generated code executes only in the sandbox.
- Task containers: no network, no secrets, no Docker socket, non-root user, dropped capabilities, no-new-privileges, resource limits, read-only root, bounded writable workspace and tmp.
- Curated dependencies are baked into a pinned image. Never install packages at agent request during a trial.
- The host holds provider credentials. They are never mounted into the task container or placed in model-visible content.
- Grader code is never mounted into the agent workspace. Evaluate final allowed artifacts in a fresh container with trusted grader code. Protect graders from modified test files and imported workspace helpers; checks need independently maintained assertions.
- Public development checks may be visible. Held-out checks remain unavailable to the generation and selection loop. This guards against accidental optimization leakage, not against malicious code.
- Only authored or manually reviewed benign fixtures are supported. Containers are a scoped execution boundary, not a certification for hostile skill packages [S2].

### 5.4 Controls and randomization

- Reset filesystem, conversation, and tool state for every condition and repetition.
- Interleave condition order within task/repetition blocks using the schedule seed. The seed reproduces scheduling and fixtures, not hosted-model sampling.
- Preserve identical task, environment, and limits across comparisons. Record provider behavior settings and request times.
- A/A trials measure harness noise and model variability. Include known benign and deliberately conflicting controls, labeled as constructed.
- Compare A+B against none, A, and B. Compare both A→B and B→A exposure orders when investigating ordering.
- **Mandatory in Phases 3–4 — no-skill stage-matched control.** A run with identical stage structure and budget but zero skills exposed. If it matches the treatment, the gain came from extra attempts and review, not instruction separation, and the claim does not hold. This control appears in the primary results table, never an appendix.
- **Mandatory in Phase 3 — matched-prompt inline arm.** Where a multi-stage policy uses a structured stage prompt, the shared arm receives the equivalent wrapper, so context isolation and prompt framing do not vary together. This is the specific confound in [S13].
- Length-matched neutral padding is an optional sensitivity experiment, not a clean causal control: padding content and position may themselves affect behavior.
- Keep selection experiments separate from forced-exposure composition experiments.
- Freeze skill content, grader definitions, and task sets for confirmation.

### 5.5 Metrics and statistical policy

Primary endpoint: task-level success requiring all declared mandatory checks. Also report check-level results without treating correlated checks as independent samples.

Secondary endpoints: unwanted file changes, invalid API usage verified by execution, model and tool calls, input/output/cache tokens, spend estimate, elapsed time. Do not equate more calls or extra files with harm unless task policy makes them undesirable.

For a task family, with p0, pA, pB, pAB the mean task success under the four conditions:

```text
pair_vs_A            = pAB - pA
pair_vs_B            = pAB - pB
additive_interaction = pAB - pA - pB + p0
```

The interaction contrast depends on the additive probability scale and is distorted by ceiling and floor effects. A negative contrast alone does not establish a harmful pair. Show individual baselines, task strata, and practical losses. Reserve "each useful alone, harmful together" for data supporting every part of that statement.

**Task difficulty calibration.** CTA found 37 of 49 tasks at ≥90% baseline pass rate, leaving no headroom for a skill effect to register. Target task families whose no-skill baseline sits roughly in the 0.4–0.8 band and verify this in Phase 1. A task that always passes or always fails carries no information about composition.

Screening uses descriptive effects and sample sizes; three repetitions are a debugging default, not a confidence guarantee. Confirmation sample size is chosen from pilot variability and a declared practically meaningful loss, before confirmation begins. Store the rationale; never auto-promote from three runs.

For suite-level uncertainty, implement a paired hierarchical bootstrap: resample task families when generalizing across families, then tasks within family and repetitions within tasks, keeping condition blocks aligned. With too few families, restrict claims to the fixed benchmark and report task-level variation rather than manufacturing population precision. Use a deterministic analysis seed and report the method. Sparse or degenerate outcomes require a conservative interval or `insufficient_evidence`, never a zero-width interval.

Single-case estimates use binomial success intervals; comparisons must account for both arms. Do not assume matching repetition counts controls model randomness. McNemar's test is not a universal default for nested repeated trials.

Freeze one primary confirmation claim per demo, or apply a documented familywise correction such as Holm across predeclared confirmatory tests. Adaptive search results are exploratory. Validate selected winners with new calls on untouched tasks. No repeated peeking at fixed-sample confidence intervals to stop early; sequential stopping requires a separately implemented valid method.

For release non-inferiority, define delta = candidate minus baseline success. With predeclared margin m, a candidate passes only when the appropriate lower confidence bound exceeds −m and mandatory checks and coverage pass. No significant difference is not proof of equivalence. An upper bound below −m indicates meaningful regression; intermediate results are inconclusive. Never use low power to justify promotion. Cost gates and critical task requirements are evaluated separately.

### 5.6 Budget control

`plan` prints cells × repetitions × per-run limits and a conservative inference envelope. At concurrency 1, reserve the next request's bounded input and maximum output cost before dispatch; later concurrency requires atomic reservations. Record reserved and actual spend, including retries. Stop scheduling when the remaining budget cannot cover another request. Report interrupted cells as incomplete, never successful.

Multi-stage policies reserve budget for **all** planned stages before the first dispatch, so a run cannot strand mid-policy with an unusable partial result.

Offline analysis and UI tests are free. Live campaigns are opt-in. This specification creates no cron jobs, paid background loops, or automatic publishing.

---

## 6. Phase 1 — A trustworthy laboratory, and a conflict you can reproduce

**Outcome:** run one task with and without a skill, inspect exactly what was exposed, executed, changed, and scored — and see a deliberately conflicting skill pair reproduce a measurable degradation.

### Tickets, in order

1. **P1.1 Package skeleton** — CLI, schemas, artifact hashing, scripted backend, test/lint CI, `doctor` command, public repository with README and Apache-2.0 license.
2. **P1.2 Skill ingestion** — parse package metadata; snapshot body and references; validate paths and file sizes; expose a readable inventory. Preserve unknown optional metadata as data, never as execution authority.
3. **P1.3 Task engine** — constrained Docker workspace and trusted evaluator; four small Python/JSON tasks with explicit requirements. **Verify no-skill baseline success falls in the 0.4–0.8 band; retune difficulty if not.** Everything downstream is noise if tasks saturate.
4. **P1.4 Runner with stage abstraction** — bounded client-tool loop wrapped in a stage scheduler executing a `stage_plan` of length 1 in this phase. Forced skill exposure, event logging with `stage_id`, termination classification, Anthropic backend behind the backend protocol. Verify official provider tool-use documentation [S3] before writing provider calls. Do not special-case single-stage execution.
5. **P1.5 Campaign planner** — none/A conditions, repetitions, interleaved order, budget reservation, crash-safe persistence, resume semantics, preregistration hash binding.
6. **P1.6 Constructed conflict fixture** — author two skills with a deliberate, documented directive conflict, drawn from genuinely reasonable instructions that happen to collide rather than direct contradictions. Suggested shape: a migration skill encouraging broad edits against a minimal-diff review skill discouraging them. Run the four-condition grid. **Exit requirement: the pair shows reproducible degradation relative to both singletons across repetitions, or the fixture is redesigned until it does.** This is the pipeline's positive control and the guaranteed input to Phase 3.
7. **P1.7 Report** — conditions side by side, assertion results, usage, file diff, ordered observable events.

### Initial task families

- **JSON configuration** — produce parseable JSON satisfying an explicit schema, with no unrelated files.
- **Small Python repair** — fix a boundary bug while preserving public behavior.
- **API migration** in a toy pinned library — use valid current methods, verified by executable tests.
- **Robust input handling** — handle declared invalid inputs without breaking valid cases.

Authored skills: `minimal-change`, `edge-case-checklist`, plus the constructed conflicting pair. These fixtures establish pipeline behavior, not ecosystem prevalence, and every report must say so.

### Exit criteria

- Scripted runs verify known pass/fail/invalid/limit cases exactly.
- Live pilot: 4 tasks × 2 conditions × 3 repetitions = 24 runs, budget permitting.
- Task baselines verified inside the 0.4–0.8 band.
- Constructed conflict pair reproduces degradation (P1.6).
- Measured per-run cost recorded; §4.5 budget table updated with real numbers.
- A/A subset run; variance shown without asserting backend determinism.
- A fresh checkout generates an offline example report with no key and no network.
- Meaningful tests for grader tampering, filesystem escape, timeout, missing pricing, and corrupt resume state.
- A single-stage run and a scripted two-stage run both execute through the stage scheduler.
- Every report discloses backend, model, fixture origin, N, status counts, and environment identity.

### Write-up angle

**"I built a lab to see whether an agent skill changes the result — or just the work."**

Walk through skill content → executed task → result and diff. Close with the constructed conflict as a teaser — two sensible skills, measurably worse together — explicitly labeled as deliberately constructed to validate the instrument. Publish the runnable example and the repository link. Do not claim you proved skills hurt, that the constructed case represents real skills, or that you invented skill evaluation.

---

## 7. Phase 2 — Does this happen with skills nobody designed to conflict?

**Outcome:** determine whether an observed problem comes from one skill, its combination with another, or selection behavior — using skills written to be useful, not to collide.

### Tickets

1. **P2.1 Four-condition planner** — none/A/B/A+B per candidate pair, deduplicating identical planned singleton and control cells within one frozen study. Shared controls create correlated comparisons; analysis must retain that identity.
2. **P2.2 Collection inventory** — four benign authored skills: `minimal-change`, `edge-case-checklist`, `migration-guide`, `implementation-review`. Record hypotheses in `docs/preregistration/phase-02.yaml` before running.
3. **P2.3 Analysis** — task-wise effects, family strata, interaction contrast, intervals, `screening` vs `confirmation` labels.
4. **P2.4 Exposure tracking** — discovery mode and explicit load tools. Separate catalog visibility, body exposure, and reference exposure.
5. **P2.5 Evidence cards** — four conditions, outcomes, actual skill loads, changed paths, alternative explanations.
6. **P2.6 Contextual map** — clickable pair matrix filtered by task family, model, loading mode, and order. Grey means untested or inconclusive, never safe; blank cells are never imputed as compatible.

### Diagnostics

Start with observable signals: copied literals, extra writes, invalid API calls, repeated check cycles, incomplete required artifacts. Reference CTA's Skill Influence Patterns [S4] as related vocabulary; do not claim an exact reproduction or a validated SIP classifier. No generic LLM "cause explanation" counts as evidence.

Each signal carries event references and a confidence label. A copied token may be correct; a new file may be necessary. Only task checks decide outcomes. CTA-inspired explanations are hypotheses until intervention confirms them.

### Exit criteria

- Four benign skills give six pairs and eleven unique unordered sets including empty and singletons; 8 development tasks × 11 sets × 3 repetitions = 264 screening runs. A full-grid option, not mandatory spend.
- Default pilot screens two predeclared pairs; expand only within budget. Publish skipped cells.
- Re-verify the constructed pair as a positive control in the same study, alongside a benign control pair.
- One reviewed third-party pair if licensing permits, with provenance kept separate.
- Any natural interaction found is frozen and confirmed with fresh calls; unseen tasks are added before claiming family-level generality.
- **If no natural interaction survives confirmation, ship the map and publish the negative finding.** Phase 3 proceeds with the constructed pair. A null result here is a genuine contribution and does not block the core thesis.
- Statistical unit tests cover known effect tables, correlated controls, missing runs, all-pass/all-fail cells, and null simulations catching anti-conservative behavior.

### Write-up angle

**"Do two useful skills stay useful together?"**

Show the four-condition matrix and one evidence card. State whether each example is constructed or natural, the task and repetition counts, and whether confirmation succeeded. Say "candidate interaction" until supported. Link raw results and name the strongest alternative explanation. If the honest answer is "on four skills and eight tasks I could not produce a natural conflict," post exactly that — it is more interesting and more credible than a manufactured one.

---

## 8. Phase 3 — Experiment with better composition (core)

**Outcome:** test whether the same skill content works better applied differently, without rewriting or removing the skills.

### Policies

| Policy | Semantics |
|---|---|
| `shared` | One worker receives both bodies in declared order and the same task workspace |
| `phased` | Worker A implements; a fresh worker B receives the task, resulting workspace, and bounded handoff, then reviews and edits using B only |
| `isolated` | A and B independently solve from separate initial workspaces; a no-skill integrator receives bounded artifact diffs and summaries and produces the final workspace |

In `phased`, use a fresh context rather than pretending previously exposed instructions can be erased from history. Distinguish instruction isolation from artifact influence: B still sees A's work. In `isolated`, the integrator's behavior and token cost are part of the policy, not free infrastructure.

### Mandatory control arms

Both appear in the primary results table:

- **`shared-matched-prompt`** — the shared arm receives the same structured stage wrapper as multi-stage arms, so isolation and prompt framing do not vary together.
- **`no-skill-phased`** and **`no-skill-isolated`** — identical stage structure and budget, zero skills exposed. If these match the treatment, the gain came from extra attempts and review, not instruction separation.

### Cost parity

Run and report both:

- **Equal total budget** — all policies share one per-task call and token ceiling. Favors `shared`.
- **Equal per-worker budget** — each worker gets the single-worker ceiling; total cost rises with worker count. Favors multi-stage.

A policy winning under only one parity definition is reported as conditional, not as a win. Publish the quality-versus-cost curve rather than selecting the parity definition that flatters the hypothesis.

### Tickets

1. **P3.1 Composition protocol** — `prepare`, `next_stage`, `handoff`, `finalize`, with explicit stage IDs and per-stage tool permissions, built on Phase 1's stage scheduler.
2. **P3.2 Bounded handoffs** — structured `Handoff` with artifact hashes, attempted checks, known unresolved issues, and a length limit. Mark truncation; never claim a summary is lossless.
3. **P3.3 Implement policies** — shared, shared-matched-prompt, phased, isolated, plus no-skill stage-matched controls. Test both A/B orders; publish order.
4. **P3.4 Dual cost parity** — both parity modes and the combined cost curve.
5. **P3.5 Candidate ranking** — rank on predeclared task quality subject to unwanted-change and cost limits; retain Pareto tradeoffs when no policy dominates.
6. **P3.6 Report** — timeline of worker contexts and artifact flow; before/after checks and total cost; control arms adjacent to treatment arms. No visualization may imply measured causality from similarity alone.

### Exit criteria

- Freeze the constructed pair plus any natural pair from Phase 2; compare all policies on the same tasks and environments.
- Control arms run in every comparison, not as follow-up.
- Select a policy on development tasks; confirm on untouched tasks with fresh calls and frozen skill content.
- Tests establish workspace independence, per-stage budget accounting, handoff completeness flags, and grader isolation.
- A fully scripted demo shows all policies; live findings may show no improvement. Never substitute scripted behavior for a live result.
- **A null or negative result is a publishable outcome of the core experiment**, provided control arms ran. "Rearranging did not recover the benefit; removing one skill was better" is a real finding.

### Write-up angle

**"What if the problem isn't the skills — it's how they're combined?"**

The centerpiece. Show identical skill files under different arrangements, with the no-skill stage-matched control in the same chart. Publish quality/cost tradeoffs under both parity definitions. If isolation loses, explain what the trace suggests and label that tentative. Note plainly that the nearest published comparison changed prompt framing and context isolation together, and that this run separates them.

---

## 9. Phase 4 — Does the finding survive change?

**Outcome:** take Phase 3's winning arrangement and find out what it actually depends on.

A composition decision is only useful if you know its scope. This phase tests the secondary hypothesis and produces the staleness signal Phase 5 consumes. It also quantifies the cost of re-establishing confidence — the concrete version of "you have to keep testing these things."

### Transfer axes

| Axis | Manipulation | Question |
|---|---|---|
| Tasks | Held-out families never used for selection | Does it generalize beyond where it was chosen? |
| Model | One additional model, everything else frozen | Is the conflict a property of the skills or the model? |
| Skill version | Edit one skill body or referenced file | Does the decision survive ordinary maintenance? |

### Tickets

1. **P4.1 Evidence store** — query historical results by task family, package hashes, observed co-exposure, policy, model, and environment. Staleness is computed from identity changes, not asserted.
2. **P4.2 Transfer harness** — re-run the frozen winning arrangement and its control arms across each axis, holding everything else constant.
3. **P4.3 Staleness rules** — define which identity changes invalidate which comparisons. A referenced-file edit invalidates decisions even when `SKILL.md` is unchanged.
4. **P4.4 Holds/breaks matrix** — per-axis outcome with intervals and an explicit `insufficient_evidence` state.
5. **P4.5 Cost of revalidation** — report what it cost to re-establish confidence after each change.

### Exit criteria

- Each axis runs with the same control arms as Phase 3; a transfer result without controls is not reported.
- Held-out tasks were never used for policy selection, enforced by a split check in code.
- Model comparison records both requested and reported model identity.
- A skill edit demonstrably invalidates the prior decision record.
- Revalidation cost published per axis.
- Any "it generalizes" claim names the axes tested and the axes not tested.

### Write-up angle

**"The fix worked. Then I changed the model."**

Show the holds/breaks matrix. A finding that evaporates on a second model is a useful result and a strong argument for the lifecycle product. State revalidation cost explicitly.

---

## 10. Phase 5 — Close the lifecycle loop

**Outcome:** propose a collection change, run relevant experiments, review a scoped decision, promote a configuration, and revert it reproducibly.

Lifecycle management for skill libraries is crowded [S6, S7, S8, S15, S16]. Claim no novelty in the concept. The contribution is narrower: decisions are gated on measured composition and transfer evidence with declared margins, and expire automatically when identities change.

### Tickets

1. **P5.1 Collection snapshots** — immutable package/policy/environment identities and a local `current` pointer; all previous versions remain addressable.
2. **P5.2 Change classifier** — detect body, metadata, reference, tool-image, runner, or model changes. Change types select experiment templates; nothing erases mandatory checks.
3. **P5.3 Decision policy** — configured minimum coverage, non-inferiority margin, cost ceiling, critical assertions, maximum evidence age. Reports say `eligible_for_review`, `blocked`, or `inconclusive`, with scope and uncertainty.
4. **P5.4 Candidate operations** — add skill, replace version, change composition, disable skill. Automatic instruction synthesis is out of scope; human-authored candidates are evaluated identically.
5. **P5.5 Promotion and rollback** — explicit local CLI action atomically changes the current pointer only after verifying decision and snapshot hashes. Rollback restores configuration, not previously executed external side effects. No external deployment integration.
6. **P5.6 Lifecycle timeline** — skill addition, interference evidence, composition experiment, decision, environment change, evidence invalidation, revalidation.
7. **P5.7 Release polish** — install guide, offline demo, methodology, known limits, contribution instructions, licenses, redacted example bundle. Tag v0.1.

### Demonstration sequence

1. Measure a baseline and evaluate a helpful candidate skill.
2. Add a second skill; show the measured interaction or uncertainty.
3. Test composition alternatives; record a decision.
4. Change the model or a versioned toy API; mark affected evidence stale.
5. Revalidate; show a proposed retirement, new policy, or rollback.

Retirement means no useful benefit was established within declared margins on tested workflows — not that the model has permanently internalized the skill. A scripted rollback demonstration must be visibly labeled.

### Exit criteria

- Changing referenced content invalidates the relevant decision even when `SKILL.md` is unchanged.
- Invalid or incomplete studies cannot promote candidates.
- Old decisions do not authorize new model or environment identities.
- Promotion and rollback are atomic and recover from interruption.
- Offline demo runs on a fresh checkout without credentials; live mode is opt-in and budgeted.
- One end-to-end live case published if funding permits; otherwise the working product is clearly separated from unvalidated hypotheses.
- Final report compares current configuration, candidate, and baselines on untouched confirmation tasks; limitations visible above the fold.

### Write-up angle

**"A skill collection that can change — and show its work."**

Link the repository, offline demo, and methodology. State exactly what is automated: planning, execution, evidence capture, comparison, decision preparation. State that authoring, acceptance requirements, and deployment authority remain explicit. Invite one real contributed skill/task interaction rather than stars.

---

## 11. Public reporting contract

Each `docs/weekly/week-NN.md` contains:

1. Question investigated; phase release and commit.
2. What shipped, and the exact reproduction command.
3. Preregistration file hash and any deviations from it.
4. Fixture provenance: authored control, constructed conflict, reviewed third-party, or contributed.
5. Model, runner, environment, dates, task counts, repetitions, limits, spend, invalid runs.
6. Findings with uncertainty and links to supporting artifacts.
7. One surprise or failed hypothesis, and what it taught.
8. Limitations and the next experiment.
9. A 150–250 word public draft built from those facts, plus one visual.

Keep `claims.json` mapping every numeric public claim to a comparison artifact, preregistration hash, and analysis version. Never prewrite success numbers. Screenshots must show enough context to distinguish screening from confirmation and constructed fixtures from natural ones. Public exports contain no embedded model instructions and no executable trace HTML: escape all tool output and user content, neutralize script tags, never render untrusted Markdown as raw HTML.

Build progress and research results are separate. A completed feature can be published even when the hypothesis failed. There is no requirement to manufacture an increasingly impressive result each week.

---

## 12. Validation strategy

### Always-on CI, no API key

- Package parsing and hashing; reference-file invalidation.
- Scripted tool-call round trips and all termination states.
- Stage scheduler: single-stage and multi-stage plans, per-stage budget accounting, workspace independence.
- Tool broker path boundaries, evaluator isolation, resource-limit behavior.
- Campaign identity, crash recovery, retry accounting, immutable results.
- Preregistration hash binding and deviation detection.
- Statistical aggregation against known tables; null simulations; degenerate cases.
- Policy handoff semantics and **control-arm presence checks** — a comparison missing its mandatory control fails analysis.
- Held-out split enforcement.
- Lifecycle promotion guards and rollback recovery.
- HTML escaping, missing-artifact handling, public export redaction.

Use tiny fixtures that exercise real failure boundaries. Avoid tests that assert a function repeats its own implementation. Container integration tests may be a separate CI job with a clear prerequisite; absence of Docker must never masquerade as a passed sandbox test.

### Opt-in live checks

One tiny smoke task before any larger campaign; confirm recorded model identity, tool behavior, usage, and grader validity. Run additional paid checks only when a change or research question justifies them. Do not rerun until a desired result appears.

### Phase completion

A phase is complete when its functional gates pass, its offline artifact is reproducible, any live findings are honestly labeled, and its weekly evidence document exists. A research hypothesis may remain unresolved without blocking a correctly implemented phase.

---

## 13. Risks and fallbacks

| Risk | Response |
|---|---|
| No natural harmful pair in Phase 2 | Publish the null result; proceed with the constructed pair; state provenance everywhere |
| Constructed pair does not reproduce in Phase 1 | Redesign the fixture until it does — this is the instrument's positive control |
| Tasks saturate at ceiling | Retune difficulty into the 0.4–0.8 baseline band before building further phases on them |
| API costs exceed budget | Cut task breadth and policy count; protect control arms over breadth; reuse immutable results for analysis only, never as new trials |
| Effect disappears with repeats | Mark the original unconfirmed; keep the data |
| No arrangement beats shared | Valid result for the core hypothesis, provided controls ran; report policy costs and failures |
| Control arm matches treatment | Report that the gain came from extra attempts, not instruction separation — the most important negative result this project can produce |
| Finding does not transfer to a second model | Report it; this strengthens the lifecycle argument |
| Custom runner differs from native tools | Limit claims to this runner; native adapter validation is a later milestone |
| Week exceeds available time | Cut optional breadth, never validity checks; post implementation progress rather than claiming phase completion |

**Deferred beyond these phases:** budgeted or evidence-guided experiment selection and its retrospective evaluator, automatic skill generation, sentence-level skill editing, cross-user evidence pooling, hypergraph learning, native adapters for multiple coding products, hosted dashboards, marketplace integration, always-on production agents, causal guarantees, arbitrary malicious-code execution, automated external deployment.

The full vision remains broader: a portable, experimentally maintained map of skill usefulness across tasks, models, environments, and execution arrangements. These five phases build the measurement and decision machinery needed to investigate it.

---

## 14. Implementation instructions

This is a target specification. CLI commands, interfaces, and modules are proposed until implemented. **Start with Phase 1 only; do not build all five phases in one pass.**

1. Inspect the target repository and any applicable `AGENTS.md` / `CLAUDE.md`. Preserve existing work.
2. Keep one authoritative copy of this spec at the repository root.
3. Write a small implementation checklist for the current phase, referencing ticket IDs.
4. Build the scripted backend and task evaluator before paid inference integration.
5. Implement the runner behind a stage-scheduler abstraction even though Phase 1 uses one stage. Do not inline single-stage assumptions.
6. Pin dependencies with a lockfile. Verify official API documentation before writing provider-specific calls.
7. Implement the smallest end-to-end path, then add required failure-path tests.
8. Produce the offline demo and report; record verification in `docs/weekly/week-01.md`.
9. Never invent live results. Missing credentials or budget do not prevent offline progress; report the remaining live-validation step.
10. Do not push, publish a package, post publicly, create automations, or start paid campaigns unless separately authorized.
11. End each phase with what shipped, what was tested, unresolved concerns, actual spend, and the next bounded task.

### First request

> Implement Phase 1 of spec.md, beginning with P1.1–P1.3. Build the Python package, schemas, hashing, scripted backend, sandboxed task fixture, and trusted evaluator. Make one offline end-to-end example runnable without API credentials. Follow the spec's execution-status, artifact, and sandbox contracts. Design the runner entry point so a stage plan of length n is the general case, but implement only n=1 in this pass. Add meaningful tests and document what remains before P1.4. Do not run paid inference or implement later phases.

### Second request, after P1.1–P1.3 land

> Implement P1.4–P1.5: the stage scheduler and worker loop, forced skill exposure, event logging with stage_id, termination classification, the Anthropic backend behind the backend protocol, and the campaign planner with budget reservation and resume. Verify official Anthropic tool-use documentation before writing provider calls. Add a scripted two-stage test that exercises the scheduler without live inference.

### Third request

> Implement P1.6–P1.7: the constructed conflict fixture and the comparison report. The fixture must be two skills whose instructions are individually reasonable but collide in combination. Verify the no-skill baseline for each task sits between 0.4 and 0.8 before proceeding; report any task that does not. Produce the four-condition comparison report offline against the scripted backend first.

---

## 15. References and prior-art boundary

Checked 2026-09-15. These inform the design; none establishes that Squelch is first or that the proposed methods work.

- **[S1]** [Agent Skills specification](https://agentskills.io/specification) — package metadata, resources, progressive disclosure. Squelch's loading behavior is documented independently.
- **[S2]** [Docker Engine security](https://docs.docker.com/engine/security/) — isolation boundaries; informs the local threat model.
- **[S3]** [Anthropic client tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) — structured tool-call loop for the live backend.
- **[S4]** [Counterfactual Trace Auditing of LLM Agent Skills](https://arxiv.org/abs/2605.11946) — paired single-skill trace diagnostics and SIP vocabulary; r=1, no intervals, descriptive rather than causal.
- **[S5]** [Can Agent Skills Make Output Worse?](https://dacharycarey.com/2026/05/07/can-agent-skills-make-output-worse/) and [A Skill Is More than Markdown](https://dacharycarey.com/2026/05/11/agent-skill-more-than-markdown/) — lifecycle motivation; a documentation-derived skill measured 66% worse than no skill.
- **[S6]** [AgentSkillOS](https://arxiv.org/abs/2603.02176) — skill retrieval and orchestration prior art.
- **[S7]** [SkillNet](https://arxiv.org/abs/2603.04448) — organized, evaluated skill infrastructure; a registry alone is not this project's novelty.
- **[S8]** [Dynamic Agent Skills lifecycle survey](https://arxiv.org/abs/2607.10113) — admission, composition, repair, pruning across 124 papers.
- **[S9]** [The Debugging Book: Delta Debugging](https://www.debuggingbook.org/html/DeltaDebugger.html) — future subset isolation; local minimality does not imply a globally smallest stochastic cause.
- **[S10]** [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) — implement the correct sampling unit; do not bootstrap rows blindly.
- **[S11]** [pytest](https://docs.pytest.org/en/stable/) — trusted task checks and harness tests.
- **[S12]** [skill-eval-harness](https://github.com/adewale/skill-eval-harness) — paired variants, traces, evaluator hygiene as engineering prior art.
- **[S13]** [Subagents vs Agent Skills](https://arxiv.org/abs/2609.09233) — nearest work to Phase 3; varies prompt framing alongside context isolation, no matched-prompt inline arm, no intervals. Phase 3's control design responds directly to this.
- **[S14]** [SkillsBench](https://arxiv.org/abs/2602.12670) — names skill composition (synergy vs. interference) as open future work; proposes length-matched controls.
- **[S15]** [SLIM: Dynamic Skill Lifecycle Management](https://arxiv.org/abs/2605.10923) — expansion/retirement with ablations showing retirement matters materially.
- **[S16]** [SkillWiki](https://arxiv.org/abs/2606.16523) — full lifecycle governance including deprecation and archival.
- **[S17]** [A Comprehensive Survey on Agent Skills](https://arxiv.org/abs/2605.07358) — names the asymmetric-revision gap: systems add artifacts far better than they rewrite or retire them.
- **[S18]** [SKILL-MIX (Yu et al., ICLR 2024)](https://arxiv.org/abs/2310.17567) — unrelated to this work despite surface similarity; evaluates an LLM's ability to *combine language skills in generated text*, not interference between loaded agent-skill packages. Noted to avoid naming and framing confusion.

Maintain `docs/prior-art.md` as implementation proceeds. Any publishable contribution must state the precise comparison, dataset, and measured result. Useful open-source engineering remains valuable even if the research hypothesis is not supported.
