---
title: Status vs. quality
---

# Execution status is not task quality

Squelch keeps two questions strictly apart:

1. **Did the machinery work?** That is the run's **status**.
2. **Was the work correct?** That is `task_success`.

Mixing them is how a limits artifact gets blamed on a skill.

## Run status

| Status | Meaning | In the valid denominator? |
|---|---|---|
| `completed` | The agent stopped normally. May pass or fail the task. | Yes |
| `agent_limit` | The agent exhausted a declared budget (model calls, tool calls, time, or output tokens). | Yes, counted as **non-success** |
| `invalid` | Sandbox, provider, or evaluator failure. Not ordinary agent failure. | No: reported separately |
| `not_run_budget` | Never started because the token budget was exhausted. | No: reported as incomplete |
| `interrupted` | Operator interrupt or host crash. Partial artifacts kept. | No |

Every report publishes status counts *and* the valid denominator. An inconvenient run is never silently replaced.

## Termination reason

Why the agent loop ended:

| Reason | Set when |
|---|---|
| `final_response` | The model replied with text and no tool calls |
| `model_call_limit` | It used all its allowed model calls |
| `tool_call_limit` | It used all its allowed tool calls |
| `output_token_limit` | A response was cut off by the output-token cap |
| `timeout` | The per-stage wall-clock limit passed (checked between calls) |
| `backend_error` | The model backend failed |
| `operator_interrupt` | The run was interrupted with Ctrl+C |

`harness_error` also exists in the schema for infrastructure faults.

## What counts as "agent behavior"

- A provider **refusal**, or the agent choosing an **invalid tool call** (say, reading `../../etc/passwd`), is agent behavior. The error goes back to the model as a tool result and the run continues.
- A **grader crash** or **timeout** is not agent behavior. The run is `invalid`, never a fake failure.

## A real example: the truncation bug

The first live pilot recorded `stop_reason: "length"` faithfully, but the runner labelled those runs `completed` instead of `agent_limit`. The observation was sound; only the derived label was wrong. Two of 48 runs were affected, one of them the run behind the most dramatic-looking cell in the results.

That is why status and quality are separate, and why Squelch has [`replay`](../architecture/analysis.md#replay-offline-re-analysis): it re-derives labels from recorded events without re-running the model. The full story is in [Pilot 001](../results/pilot-001.md#the-instrument-was-wrong).
