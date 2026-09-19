---
sidebar_label: Week 1 report
---

# Week 01 — a lab, a live pilot, and two failed exit criteria

**Phase:** 1 (instrumented laboratory)
**Commit:** see `git log`; preregistration
`sha256:2069c94cfda3e0e965b176fb63872db847e42b9fd55f34d1cbe2bb03ad75b775`
(`docs/preregistration/phase-01.yaml`, committed before any live run)
**Spend:** $0.00. All inference ran locally on Ollama.

## 1. Question investigated

Two preregistered hypotheses:

- **H1 (positive control).** The deliberately constructed pair
  `modernize-thoroughly` + `minimal-change` degrades task success relative to
  *each* skill alone.
- **H2 (calibration).** Each task family's no-skill baseline lands in the
  0.4–0.8 band, where a skill effect has room to register.

**Neither is supported. H2 failed outright.** Details below.

## 2. What shipped

Tickets P1.1–P1.7. Skill ingestion with content-hashed package identity; a
bounded tool-calling runner behind a stage scheduler that treats an *n*-stage
plan as the general case; a Docker task-container contract plus a clearly
labeled non-isolating local fallback; a trusted evaluator that grades only
declared outputs with code the agent never sees; a campaign planner with
interleaved condition order, a token ledger, crash-safe resume and
preregistration binding; Wilson intervals and four-condition interaction
contrasts; and a self-contained HTML report.

**Deviation from the spec:** the live backend is local Ollama rather than the
Anthropic API — the operator's choice, recorded in
`docs/decisions/phase-01-checklist.md`. The backend protocol is unchanged.

### Reproduction

```bash
uv sync
uv run pytest -m "not docker"                       # 110 tests, no key, no network
uv run squelch run --config fixtures/campaigns/conflict-demo.yaml --backend scripted --study-id conflict-demo
uv run squelch report conflict-demo --out report.html
```

## 3. Fixture provenance

Every skill and task is an **authored control** written for this harness.
`modernize-thoroughly` is a **deliberately constructed conflict fixture** —
authored to collide with `minimal-change` by design. It says nothing about
how often real skills conflict, and is labeled constructed in every summary
and report.

## 4. Setup

| | |
|---|---|
| Model | `qwen3:8b` via Ollama 0.34.0, temperature 0.2, 2048 output tokens/call |
| Environment | `local:python-3.13.14:darwin` (the non-isolating local runner) |
| Design | 4 tasks × 4 conditions (none / a / b / ab) × 3 repetitions = 48 runs |
| Status counts | 46 `completed`, 2 `agent_limit`, 0 `invalid` |
| Evidence stage | `screening` — descriptive only |

## 5. Results

Successes / valid runs:

| Task | none | a (modernize) | b (minimal) | ab (pair) |
|---|---|---|---|---|
| api-migration | 1/3 | 3/3 | 3/3 | 3/3 |
| json-config | 3/3 | 3/3 | 2/3 | 3/3 |
| python-repair | 3/3 | 2/3 | 3/3 | 3/3 |
| robust-input | 3/3 | 3/3 | 3/3 | **0/3** |

Pooled, with Wilson 95% intervals:

| Condition | Rate | 95% CI |
|---|---|---|
| none | 0.83 | [0.55, 0.95] |
| a | 0.92 | [0.65, 0.99] |
| b | 0.92 | [0.65, 0.99] |
| ab | 0.75 | [0.47, 0.91] |

`pair_vs_A = −0.167` · `pair_vs_B = −0.167` ·
`additive_interaction = −0.250`

**The direction matches H1 and the evidence does not support it.** Every
interval overlaps every other interval. At 12 runs per condition these
contrasts are compatible with no effect, and with an effect in either
direction.

## 6. Why the one dramatic cell is not a finding

`robust-input` under the pair reads 3/3 → 0/3, which looks like textbook
interference. Opening the three failures shows **three unrelated causes**:

1. one run was cut off by the output-token cap and wrote nothing;
2. one emitted literal `\n` escape sequences instead of newlines, producing a
   file with an unterminated string;
3. one closed a docstring with `"` instead of `"""`.

These are mundane, independent stumbles, not a coherent response to
conflicting instructions. The same escape-sequence quirk also appears once
under `b` alone, so it is a low-rate model behavior rather than something the
pair provoked. A 0/3 cell carries a Wilson interval reaching past 0.5.

**Recorded as: not a conflict. Candidate at best, and a weak one.**

## 7. One real signal, and it is a confound

Loading skills changes how much the model writes. Output tokens per run are a
**total across all of that run's model calls**, so the table also separates how
many calls a run makes from how long each response is:

| Condition | Median output tokens / run | Median model calls / run | Mean output tokens / call | Runs truncated by the cap |
|---|---|---|---|---|
| none | 1,511 | 2.0 | 574 | 0/12 |
| b | 1,530 | 3.0 | 537 | 0/12 |
| a | 1,648 | 2.5 | 677 | 1/12 |
| ab | 2,020 | 3.0 | 718 | 1/12 |

The pair writes about a third more per run than the baseline (2,020 vs 1,511,
+34%). That comes from **both** more calls (median 3 vs 2) **and** longer
responses (718 vs 574 tokens per call, about +25%). The longer responses track
skill A, the modernize skill (677 per call on its own), and **both truncations
happened in conditions that include it**.

A condition can therefore fail by running into the output cap rather than by
reasoning worse. This is exactly the length confound the spec's length-matched
control arm exists to separate, and Phase 1 does **not** separate it. The
report prints this table beside every success rate so the confound cannot be
overlooked.

*Correction.* An earlier version of this report quoted "+43%" (2,188 vs 1,533).
That figure came from a bug in the summary code, which took the upper middle
element instead of the true median for an even sample, and it compared a
per-run total to a per-call cap. Both are fixed and covered by tests.

## 8. The surprise: the instrument was wrong

Investigating the `robust-input` failures exposed a bug in the runner. When
Ollama returned `stop_reason: "length"` — the model cut off mid-generation —
the runner recorded the run as a normal `completed` / `final_response`. Spec
§4.3 classifies an exhausted output budget as `agent_limit`. A hard limit
hitting the model was being disguised as the model simply doing badly.

Fixed, with a regression test naming the run that exposed it. Two of 48 runs
were affected.

The correction was applied by **offline re-analysis, not by re-running**: the
recorded observation was sound, only the derived label was wrong. `squelch
replay` re-derives classifications from stored events into a new derived
study, leaving the source immutable, and **refuses** when re-derivation would
not be faithful — specifically when a truncated response also requested tools,
because the corrected runner would have stopped instead of executing them and
the rest of that run never happened. Zero such cases existed here, so the
re-derivation is exact.

## 9. Limitations

- **H2 failed.** Three of four tasks sit at a 1.00 no-skill baseline on this
  model. A task everything passes cannot show a skill effect, so most of this
  grid was uninformative before it ran. Harder v2 variants are authored and
  grader-calibrated; their live baselines are not yet measured.
- **The A/A trial did not run.** Without it there is no measured noise floor,
  so there is no yardstick saying how large a real effect must be here.
- **n = 3 per cell** is a debugging default, not a confidence guarantee.
- **Length and content vary together** across conditions (§7).
- Runs executed in the **non-isolating local environment**, not the Docker
  container; the container contract is implemented and separately tested.
- Results describe this runner, this model, these authored fixtures.

## 10. Operational finding

The binding constraint is **wall clock, not money**. Measured over the 48
pilot runs: median 94 s and mean 223 s per run (about 3 hours in total, with a
long tail of slow runs whose cause was not isolated; memory pressure is one
candidate), ~1,700 input and ~1,640 output tokens per run, $0.00. A healthier
stretch of the second attempt averaged ~61 s per run, so the spread is real:
plan for hours, not minutes, and free the RAM first.

That holds only while the model fits in memory. A re-run was abandoned when
the host dropped to 436 MB free with 5.7 GB of swap in use: single model calls
stretched from ~20 s to 14 minutes as the 5 GB model was paged in and out. A
local-inference lab is gated on free RAM, and that belongs in any plan for
Phase 2's 264-run grid.

It also exposed a real gap: the task timeout is checked *between* model calls,
so one very slow call runs past it. Recorded, not yet fixed.

## 11. Next bounded tasks

1. Measure live baselines for the v2 tasks; keep only families landing in
   0.4–0.8.
2. Run the A/A trial to establish the noise floor.
3. Redesign the constructed conflict so the two skills demand *observably
   incompatible artifacts* the grader already measures — the current pair's
   advice is too easily satisfied by a model that simply adds type hints.
4. Preempt a hung request mid-call rather than only between calls.

## 12. Public draft (150–250 words)

> I built a lab to test whether agent skills interfere with each other, and
> the first real experiment mostly tested my own instrument.
>
> The setup: four small coding tasks, four conditions — no skills, skill A,
> skill B, both — three repetitions each, graded by code the agent never
> sees. 48 runs on a local 8B model, $0.
>
> The headline cell looked perfect. On one task, no-skill scored 3/3, each
> skill alone 3/3, and the pair 0/3. Textbook interference.
>
> It wasn't. The three failures had three unrelated causes: one run cut off by
> a token cap, one that emitted `\n` as literal characters, one that closed a
> docstring with the wrong quotes. Three ordinary stumbles that happened to
> land in the same box. With three runs per box, that is noise.
>
> Worse for me: chasing it exposed a bug in my own runner. Responses cut off
> by the token limit were being filed as normal completions — a hard limit
> disguised as the model doing badly.
>
> Two other things showed up. Three of my four tasks were so easy that
> everything passed them, so they could never have revealed anything. And
> loading both skills made the model write about a third more per run — which
> means length and content varied together, and I can't yet tell them apart.
>
> No finding. A working lab, a fixed bug, and a much better idea of what to
> measure next.
