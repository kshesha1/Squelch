"""Per-condition verbosity and truncation diagnostics.

Loading more instructions lengthens both the prompt and the model's output,
so a condition can fail by running into an output limit rather than by
reasoning worse. That is a limits artifact, not an instruction effect, and it
has to be readable next to every success rate.

Two distinctions matter and are kept explicit here:

- ``output_tokens`` on a run is a **total across all of its model calls**. It
  is not comparable to the per-call output cap. A condition can be higher
  because it makes more calls, because each response is longer, or both, so
  the number of calls and the mean tokens *per call* are reported too.
- The median is a true median (the mean of the two middle values for an even
  sample), not the upper middle element.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable

from squelch.schemas import RunResult, RunStatus, TerminationReason

_VALID = (RunStatus.COMPLETED, RunStatus.AGENT_LIMIT)


def condition_diagnostics(items: Iterable[tuple[str, RunResult]]) -> list[dict]:
    """Summarise verbosity and truncation per condition.

    ``items`` is (condition_id, result) pairs. Only runs that reached grading
    (``completed`` or ``agent_limit``) are counted, matching the valid
    denominator used for success rates.
    """
    per: dict[str, list[RunResult]] = {}
    for condition_id, result in items:
        if result.status in _VALID:
            per.setdefault(condition_id, []).append(result)

    out: list[dict] = []
    for condition_id in sorted(per):
        runs = per[condition_id]
        totals = [r.usage.output_tokens for r in runs]
        calls = [sum(s.model_calls for s in r.stage_results) for r in runs]
        total_calls = sum(calls)
        out.append({
            "condition_id": condition_id,
            "n": len(runs),
            "median_output_tokens": int(round(statistics.median(totals))),
            "max_output_tokens": max(totals),
            "median_model_calls": statistics.median(calls),
            "mean_output_tokens_per_call": round(sum(totals) / total_calls) if total_calls else 0,
            "truncated_runs": sum(
                1 for r in runs if r.termination_reason is TerminationReason.OUTPUT_TOKEN_LIMIT
            ),
        })
    return out
