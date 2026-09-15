"""End-to-end offline demo: the full scripted campaign with no network/key.

This is the exit-criterion path: a fresh checkout generates an offline
example study and report.
"""

import json
from pathlib import Path

import pytest

from squelch.experiments.campaign import load_campaign, run_campaign
from squelch.reporting.report import render_study_report

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
CAMPAIGN = FIXTURES / "campaigns" / "offline-demo.yaml"


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("results")
    cfg = load_campaign(CAMPAIGN)
    study_id, results = run_campaign(cfg, results_root=root, study_id="itest")
    return root, study_id, results


def test_all_runs_complete(study):
    _, _, results = study
    assert len(results) == 8
    assert all(r.status.value == "completed" for r in results)


def test_scripted_conditions_diverge_as_designed(study):
    """The flawed 'none' transcripts fail grading; 'skill' transcripts pass.

    This validates the pipeline can register a between-condition difference.
    It is a program test, not a model claim.
    """
    root, study_id, _ = study
    summary = json.loads((root / study_id / "study.json").read_text())
    by_cell = {(c["task_id"], c["condition_id"]): c for c in summary["cells"]}
    for task in ("json-config", "python-repair", "api-migration", "robust-input"):
        assert by_cell[(task, "none")]["successes"] == 0
        assert by_cell[(task, "skill")]["successes"] == 1


def test_artifacts_and_traces_written(study):
    root, study_id, results = study
    for r in results:
        run_dir = root / study_id / "runs" / r.run_id
        assert (run_dir / "events.jsonl").exists()
        assert (run_dir / "result.json").exists()
        assert (run_dir / "run_spec.json").exists()
        assert "final_workspace" in r.artifact_hashes


def test_summary_discloses_scripted_provenance(study):
    root, study_id, _ = study
    summary = json.loads((root / study_id / "study.json").read_text())
    assert summary["evidence_stage"] == "scripted"
    assert "never a model-performance claim" in summary["disclosure"]
    assert summary["status_counts"] == {"completed": 8}


def test_report_renders_and_escapes(study, tmp_path):
    root, study_id, _ = study
    # Inject hostile content into a copy of the summary to verify escaping.
    summary_path = root / study_id / "study.json"
    summary = json.loads(summary_path.read_text())
    summary["campaign"] = 'demo<script>alert("x")</script>'
    hostile_dir = tmp_path / "hostile"
    hostile_dir.mkdir()
    (hostile_dir / "study.json").write_text(json.dumps(summary))

    out = render_study_report(hostile_dir, tmp_path / "report.html")
    html = out.read_text()
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "Disclosure" in html
