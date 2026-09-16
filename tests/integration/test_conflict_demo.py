"""Four-condition conflict demo end to end (P1.6 machinery, scripted)."""

import json
from pathlib import Path

import pytest

from squelch.experiments.campaign import load_campaign, run_campaign
from squelch.reporting.report import render_study_report

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
CAMPAIGN = FIXTURES / "campaigns" / "conflict-demo.yaml"


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("results")
    cfg = load_campaign(CAMPAIGN)
    study_id, results = run_campaign(cfg, results_root=root, study_id="ctest")
    return root, study_id, results


def test_scripted_conflict_pattern(study):
    """Singletons pass, the pair fails — the scripted degradation pattern."""
    root, study_id, _ = study
    summary = json.loads((root / study_id / "study.json").read_text())
    by_cell = {(c["task_id"], c["condition_id"]): c for c in summary["cells"]}
    for task in ("python-repair", "api-migration"):
        assert by_cell[(task, "none")]["successes"] == 1
        assert by_cell[(task, "a")]["successes"] == 1
        assert by_cell[(task, "b")]["successes"] == 1
        assert by_cell[(task, "ab")]["successes"] == 0


def test_diff_artifacts_written(study):
    root, study_id, results = study
    for r in results:
        run_dir = root / study_id / "runs" / r.run_id
        assert (run_dir / "diff.patch").exists()
        assert r.changed_files, f"{r.run_id} recorded no file changes"
    # The ab python-repair run added an unrequested helper module.
    ab_runs = [
        r for r in results
        if json.loads((root / study_id / "runs" / r.run_id / "run_spec.json")
                      .read_text())["condition_id"] == "ab"
    ]
    assert any(
        any("bounds_helpers.py" in c for c in r.changed_files) for r in ab_runs
    )


def test_report_contains_interaction_analysis(study, tmp_path):
    root, study_id, _ = study
    out = render_study_report(root / study_id, tmp_path / "report.html")
    html = out.read_text()
    assert "Four-condition interaction analysis" in html
    assert "ALL TASKS (pooled)" in html
    assert "additive_interaction" in html
    # ceiling/floor caveat must be visible for saturated scripted cells
    assert "ceiling" in html


def test_both_skill_bodies_exposed_in_ab_events(study):
    root, study_id, results = study
    for r in results:
        spec = json.loads(
            (root / study_id / "runs" / r.run_id / "run_spec.json").read_text()
        )
        if spec["condition_id"] != "ab":
            continue
        events = [json.loads(line) for line in
                  open(root / study_id / "runs" / r.run_id / "events.jsonl")]
        loaded = [e["payload"]["skill_id"] for e in events if e["type"] == "skill_loaded"]
        assert loaded == ["modernize-thoroughly", "minimal-change"]
