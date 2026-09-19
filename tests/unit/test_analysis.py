import pytest

from squelch.analysis.effects import four_condition_effects, wilson_interval


def test_wilson_known_values():
    lo, hi = wilson_interval(8, 10)
    # Known Wilson 95% interval for 8/10: about (0.49, 0.94)
    assert lo == pytest.approx(0.4901, abs=0.01)
    assert hi == pytest.approx(0.9433, abs=0.01)


def test_wilson_never_zero_width_at_boundaries():
    lo, hi = wilson_interval(0, 5)
    assert lo == 0.0 and hi > 0.3
    lo, hi = wilson_interval(5, 5)
    assert hi == 1.0 and lo < 0.7


def test_wilson_rejects_empty_cell():
    with pytest.raises(ValueError):
        wilson_interval(0, 0)


def test_four_condition_contrasts_known_table():
    # p0=0.5, pA=0.75, pB=0.75, pAB=0.25
    eff = four_condition_effects({
        "none": (2, 4), "a": (3, 4), "b": (3, 4), "ab": (1, 4),
    })
    assert eff.pair_vs_a == pytest.approx(-0.5)
    assert eff.pair_vs_b == pytest.approx(-0.5)
    # 0.25 - 0.75 - 0.75 + 0.5 = -0.75
    assert eff.additive_interaction == pytest.approx(-0.75)
    assert not eff.insufficient


def test_missing_condition_is_insufficient_never_imputed():
    eff = four_condition_effects({"none": (2, 4), "a": (3, 4), "b": (3, 4)})
    assert eff.insufficient
    assert eff.additive_interaction is None
    assert any("'ab'" in n for n in eff.notes)


def test_empty_cell_is_insufficient():
    eff = four_condition_effects({
        "none": (2, 4), "a": (0, 0), "b": (3, 4), "ab": (1, 4),
    })
    assert eff.insufficient


def test_ceiling_cells_are_flagged():
    eff = four_condition_effects({
        "none": (4, 4), "a": (4, 4), "b": (4, 4), "ab": (2, 4),
    })
    assert any("ceiling" in n for n in eff.notes)


def test_null_table_shows_no_interaction():
    eff = four_condition_effects({
        "none": (2, 4), "a": (2, 4), "b": (2, 4), "ab": (2, 4),
    })
    assert eff.additive_interaction == pytest.approx(0.0)


# ---- verbosity / truncation diagnostics ------------------------------------

from squelch.analysis.diagnostics import condition_diagnostics  # noqa: E402
from squelch.schemas import (  # noqa: E402
    RunResult,
    RunStatus,
    StageResult,
    TerminationReason,
    TokenUsage,
)


def _result(run_id, out_tokens, calls, *, status=RunStatus.COMPLETED,
            termination=TerminationReason.FINAL_RESPONSE):
    return RunResult(
        run_id=run_id, status=status, task_success=True,
        usage=TokenUsage(output_tokens=out_tokens),
        termination_reason=termination,
        stage_results=[StageResult(
            stage_id="s", worker_id="w", exposed_skill_ids=[], model_calls=calls,
            tool_calls=0, usage=TokenUsage(), handoff_produced=False,
            termination_reason=termination)],
    )


def test_median_is_true_median_for_even_samples():
    """Regression: the old code took the upper middle element (index n//2)."""
    items = [("c", _result(f"r{i}", t, 2)) for i, t in enumerate([100, 200, 300, 400])]
    (d,) = condition_diagnostics(items)
    assert d["median_output_tokens"] == 250  # mean of 200 and 300, not 300


def test_output_is_per_run_total_and_per_call_is_reported_separately():
    # Same total output, but one condition makes twice as many calls: the
    # per-call mean must expose that the responses are not longer.
    few = [("few", _result(f"a{i}", 1000, 2)) for i in range(3)]
    many = [("many", _result(f"b{i}", 1000, 4)) for i in range(3)]
    d = {x["condition_id"]: x for x in condition_diagnostics(few + many)}
    assert d["few"]["median_output_tokens"] == d["many"]["median_output_tokens"] == 1000
    assert d["few"]["mean_output_tokens_per_call"] == 500
    assert d["many"]["mean_output_tokens_per_call"] == 250
    assert d["many"]["median_model_calls"] == 4


def test_truncated_runs_counted_and_invalid_runs_excluded():
    items = [
        ("c", _result("ok", 500, 2)),
        ("c", _result("cut", 2048, 2, status=RunStatus.AGENT_LIMIT,
                      termination=TerminationReason.OUTPUT_TOKEN_LIMIT)),
        ("c", _result("bad", 9999, 1, status=RunStatus.INVALID)),
    ]
    (d,) = condition_diagnostics(items)
    assert d["n"] == 2  # the invalid run is not in the valid denominator
    assert d["truncated_runs"] == 1
    assert d["max_output_tokens"] == 2048
