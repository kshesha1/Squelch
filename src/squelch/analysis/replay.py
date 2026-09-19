"""Offline re-analysis of stored artifacts (spec §4.4 `replay`).

Replay never contacts a model and never re-executes an agent. It re-derives
a run's classification from the events that were already recorded, using the
*current* classification rules, and writes the result as a new derived study.
The source study is never mutated — artifacts are immutable.

This exists because a classification rule can be wrong while the underlying
observation is fine. Squelch's first live pilot recorded
``stop_reason: "length"`` faithfully but labeled those runs `completed`
instead of `agent_limit`. The observation was sound; only the derived label
needed fixing.

**Validity condition.** Re-derivation reproduces what the fixed runner would
have done only when the corrected rule would not have changed the *execution
path* — for truncation, that means the truncated response requested no tools
(had it requested tools, the old runner would have executed them and
continued, and no amount of re-analysis can invent the run that never
happened). :func:`check_replay_validity` verifies this and refuses otherwise.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from squelch.analysis.diagnostics import condition_diagnostics
from squelch.runner.stage import TRUNCATION_STOP_REASONS
from squelch.schemas import RunResult, RunStatus, TerminationReason

ANALYSIS_VERSION = "replay/1"

_LIMIT_TO_REASON = {
    "max_model_calls": TerminationReason.MODEL_CALL_LIMIT,
    "max_tool_calls": TerminationReason.TOOL_CALL_LIMIT,
    "task_timeout_seconds": TerminationReason.TIMEOUT,
    "max_output_tokens": TerminationReason.OUTPUT_TOKEN_LIMIT,
}


class ReplayError(RuntimeError):
    """Re-analysis cannot faithfully reproduce the corrected run."""


@dataclass(frozen=True)
class ReplayValidity:
    ok: bool
    reasons: list[str]


def load_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def check_replay_validity(events: list[dict]) -> ReplayValidity:
    """Refuse re-analysis where the corrected rule changes the execution path."""
    reasons = []
    for e in events:
        if e["type"] != "model_response":
            continue
        if e["payload"].get("stop_reason") in TRUNCATION_STOP_REASONS \
                and e["payload"].get("tool_call_count", 0) > 0:
            reasons.append(
                f"event {e['event_id']}: truncated response also requested "
                f"{e['payload']['tool_call_count']} tool call(s); the corrected runner "
                "would have stopped instead of executing them, so the remainder of "
                "this run never happened and cannot be re-derived"
            )
    return ReplayValidity(ok=not reasons, reasons=reasons)


def derive_termination(events: list[dict]) -> TerminationReason:
    """Re-derive a run's termination reason from its recorded events."""
    for e in events:
        if e["type"] == "run_error":
            kind = e["payload"].get("kind")
            if kind == "interrupt":
                return TerminationReason.OPERATOR_INTERRUPT
            if kind == "backend":
                return TerminationReason.BACKEND_ERROR
            return TerminationReason.HARNESS_ERROR
        if e["type"] == "limit_reached":
            reason = _LIMIT_TO_REASON.get(e["payload"].get("limit"))
            if reason is not None:
                return reason
        if e["type"] == "model_response" and \
                e["payload"].get("stop_reason") in TRUNCATION_STOP_REASONS:
            # The corrected runner stops at the first truncated response.
            return TerminationReason.OUTPUT_TOKEN_LIMIT
    return TerminationReason.FINAL_RESPONSE


def reclassify(result: RunResult, events: list[dict]) -> RunResult:
    """Return the run's result with status/termination re-derived.

    Assertions are untouched: grading was never in question.
    """
    validity = check_replay_validity(events)
    if not validity.ok:
        raise ReplayError("; ".join(validity.reasons))

    termination = derive_termination(events)
    if termination in (TerminationReason.BACKEND_ERROR, TerminationReason.HARNESS_ERROR):
        status, success = RunStatus.INVALID, None
    elif termination is TerminationReason.OPERATOR_INTERRUPT:
        status, success = RunStatus.INTERRUPTED, None
    elif termination is TerminationReason.FINAL_RESPONSE:
        status = RunStatus.COMPLETED
        success = all(a.passed for a in result.assertions if a.mandatory) \
            if result.assertions else None
    else:
        # Any exhausted budget counts as non-success for the task endpoint.
        status, success = RunStatus.AGENT_LIMIT, False

    stages = [
        s.model_copy(update={"termination_reason": termination})
        if i == len(result.stage_results) - 1 else s
        for i, s in enumerate(result.stage_results)
    ]
    return result.model_copy(update={
        "status": status,
        "task_success": success,
        "termination_reason": termination,
        "stage_results": stages,
    })


def replay_study(source_dir: Path, dest_dir: Path) -> dict:
    """Re-analyze every run of a study into a new derived study directory."""
    source_dir, dest_dir = Path(source_dir), Path(dest_dir)
    source_summary = json.loads((source_dir / "study.json").read_text(encoding="utf-8"))
    if dest_dir.exists():
        raise ReplayError(f"destination study already exists: {dest_dir}")
    (dest_dir / "runs").mkdir(parents=True)

    changed: list[dict] = []
    results: list[RunResult] = []
    for run_dir in sorted((source_dir / "runs").iterdir()):
        result_file = run_dir / "result.json"
        events_file = run_dir / "events.jsonl"
        if not result_file.is_file():
            continue
        original = RunResult.model_validate_json(result_file.read_text(encoding="utf-8"))
        events = load_events(events_file) if events_file.is_file() else []
        updated = reclassify(original, events) if events else original

        out_run = dest_dir / "runs" / run_dir.name
        out_run.mkdir(parents=True)
        (out_run / "result.json").write_text(
            json.dumps(updated.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8")
        if (run_dir / "run_spec.json").is_file():
            shutil.copy2(run_dir / "run_spec.json", out_run / "run_spec.json")
        (out_run / "source.json").write_text(
            json.dumps({"source_run_dir": str(run_dir.resolve()),
                        "note": "events, diff and workspace remain in the source study"},
                       indent=2), encoding="utf-8")
        results.append(updated)
        if (original.status, original.termination_reason) != \
                (updated.status, updated.termination_reason):
            changed.append({
                "run_id": original.run_id,
                "was": {"status": original.status.value,
                        "termination_reason": (original.termination_reason.value
                                               if original.termination_reason else None),
                        "task_success": original.task_success},
                "now": {"status": updated.status.value,
                        "termination_reason": updated.termination_reason.value,
                        "task_success": updated.task_success},
            })

    summary = _rebuild_summary(source_summary, dest_dir, results, changed)
    (dest_dir / "study.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _rebuild_summary(source_summary: dict, dest_dir: Path,
                     results: list[RunResult], changed: list[dict]) -> dict:
    by_id = {r.run_id: r for r in results}
    cells: dict[tuple[str, str], dict] = {}
    status_counts: dict[str, int] = {}
    valid_pairs: list[tuple[str, RunResult]] = []
    for run_dir in sorted((dest_dir / "runs").iterdir()):
        spec_file = run_dir / "run_spec.json"
        if not spec_file.is_file():
            continue
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        r = by_id.get(spec["run_id"])
        if r is None:
            continue
        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
        key = (spec["task"]["task_id"], spec["condition_id"])
        cell = cells.setdefault(key, {"task_id": key[0], "condition_id": key[1],
                                      "n": 0, "successes": 0, "valid_n": 0, "runs": []})
        cell["n"] += 1
        cell["runs"].append(r.run_id)
        if r.status in (RunStatus.COMPLETED, RunStatus.AGENT_LIMIT):
            cell["valid_n"] += 1
            if r.task_success:
                cell["successes"] += 1
        valid_pairs.append((key[1], r))

    diagnostics = condition_diagnostics(valid_pairs)

    summary = dict(source_summary)
    summary.update({
        "campaign": source_summary["campaign"] + " (re-analyzed)",
        "status_counts": status_counts,
        "total_runs": len(results),
        "cells": sorted(cells.values(), key=lambda c: (c["task_id"], c["condition_id"])),
        "condition_diagnostics": diagnostics,
        "derived_from": source_summary.get("campaign"),
        "analysis_version": ANALYSIS_VERSION,
        "reclassified_runs": changed,
        "disclosure": (
            source_summary.get("disclosure", "")
            + f" RE-ANALYSIS ({ANALYSIS_VERSION}): classifications were re-derived "
              "offline from the recorded events of the original study. No model was "
              "called and no agent was re-executed; grading is unchanged. "
            + (f"{len(changed)} run(s) changed classification."
               if changed else "No run changed classification.")
        ),
    })
    return summary
