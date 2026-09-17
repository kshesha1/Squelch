"""P1.5 behaviors: resume semantics, immutability, budget ledger, prereg."""

import json
import shutil
from pathlib import Path

import pytest

from squelch.experiments.campaign import (
    CampaignConfigError,
    load_campaign,
    plan_runs,
    run_campaign,
)
from squelch.experiments.tasks import load_task_manifest
from squelch.skills.loader import load_inventory

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
CAMPAIGN = FIXTURES / "campaigns" / "offline-demo.yaml"


def test_existing_study_without_resume_is_refused(tmp_path):
    cfg = load_campaign(CAMPAIGN)
    run_campaign(cfg, results_root=tmp_path, study_id="s1")
    with pytest.raises(CampaignConfigError, match="immutable"):
        run_campaign(cfg, results_root=tmp_path, study_id="s1")


def test_resume_reuses_completed_runs(tmp_path):
    cfg = load_campaign(CAMPAIGN)
    sid, first = run_campaign(cfg, results_root=tmp_path, study_id="s1")
    # Remove one run's artifacts to simulate a crash mid-campaign.
    victim = first[3].run_id
    shutil.rmtree(tmp_path / "s1" / "runs" / victim)

    sid2, second = run_campaign(cfg, results_root=tmp_path, study_id="s1", resume=True)
    assert sid2 == sid
    assert len(second) == len(first)
    summary = json.loads((tmp_path / "s1" / "study.json").read_text())
    assert summary["reused_runs"] == len(first) - 1
    # The victim was re-executed and its artifacts restored.
    assert (tmp_path / "s1" / "runs" / victim / "result.json").exists()


def test_resume_with_changed_config_is_refused(tmp_path):
    cfg = load_campaign(CAMPAIGN)
    run_campaign(cfg, results_root=tmp_path, study_id="s1")
    prior = json.loads((tmp_path / "s1" / "study.json").read_text())
    prior["config_hash"] = "sha256:different"
    (tmp_path / "s1" / "study.json").write_text(json.dumps(prior))
    with pytest.raises(CampaignConfigError, match="different config"):
        run_campaign(cfg, results_root=tmp_path, study_id="s1", resume=True)


def test_corrupt_resume_artifacts_are_rerun_not_trusted(tmp_path):
    cfg = load_campaign(CAMPAIGN)
    _, first = run_campaign(cfg, results_root=tmp_path, study_id="s1")
    victim = first[0].run_id
    (tmp_path / "s1" / "runs" / victim / "result.json").write_text("{corrupt")
    _, second = run_campaign(cfg, results_root=tmp_path, study_id="s1", resume=True)
    result = json.loads((tmp_path / "s1" / "runs" / victim / "result.json").read_text())
    assert result["status"] == "completed"  # re-executed cleanly


def test_token_budget_stops_scheduling(tmp_path):
    # Scripted steps charge 100 input tokens per model call; a tiny budget
    # exhausts after the first runs and the remainder become not_run_budget.
    text = CAMPAIGN.read_text() + "\nbudget:\n  max_total_input_tokens: 250\n"
    cfg_file = FIXTURES / "campaigns" / "tiny-budget-test.yaml"
    cfg_file.write_text(text)
    try:
        cfg = load_campaign(cfg_file)
        _, results = run_campaign(cfg, results_root=tmp_path, study_id="s1")
    finally:
        cfg_file.unlink()
    statuses = [r.status.value for r in results]
    assert "not_run_budget" in statuses
    assert statuses.index("not_run_budget") > 0  # some runs did execute
    # not-run cells are persisted, never dropped
    skipped = next(r for r in results if r.status.value == "not_run_budget")
    stored = json.loads(
        (tmp_path / "s1" / "runs" / skipped.run_id / "result.json").read_text()
    )
    assert stored["status"] == "not_run_budget"
    assert stored["task_success"] is None


def test_live_campaign_requires_preregistration(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '1'\nname: bad\nbackend: ollama\n"
        "model: {id: 'test:1b'}\n"
        "dataset: {manifest: ../tasks/development.yaml}\n"
        "conditions: [{id: a, skills: []}]\nrepetitions: 1\nschedule_seed: 1\n"
    )
    with pytest.raises(CampaignConfigError, match="preregistration"):
        load_campaign(bad)


def test_declared_but_missing_prereg_file_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '1'\nname: bad\nbackend: ollama\n"
        "model: {id: 'test:1b'}\npreregistration: nonexistent.yaml\n"
        "dataset: {manifest: ../tasks/development.yaml}\n"
        "conditions: [{id: a, skills: []}]\nrepetitions: 1\nschedule_seed: 1\n"
    )
    with pytest.raises(CampaignConfigError, match="missing"):
        load_campaign(bad)


def test_prereg_hash_recorded_in_study(tmp_path):
    cfg = load_campaign(FIXTURES / "campaigns" / "conflict-pilot.yaml")
    assert cfg.preregistration_hash is not None
    assert cfg.preregistration_hash.startswith("sha256:")


def test_unpriced_provider_is_marked_cost_unknown():
    """A backend with no price table must never imply a known cost.

    Spec §4.5: without valid prices a campaign cannot claim a dollar cap.
    Local inference has a known zero marginal cost; anything else defaults to
    cost_unknown until a price reference exists.
    """
    from squelch.schemas import ModelSpec

    unpriced = ModelSpec(provider="some-hosted-api", requested_model_id="x")
    assert unpriced.cost_unknown is True
    assert unpriced.pricing_reference is None

    cfg = load_campaign(FIXTURES / "campaigns" / "conflict-pilot.yaml")
    fixtures = load_task_manifest(cfg.dataset_manifest, cfg.graders_root,
                                  environment_image="local:test")
    skills = load_inventory(cfg.skills_root)
    specs = plan_runs(cfg, fixtures, skills, study_id="s", environment_identity="local:test")
    model = specs[0].model
    assert model.provider == "ollama"
    assert model.cost_unknown is False
    assert model.pricing_reference == "local_inference_zero_marginal_cost"
