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
