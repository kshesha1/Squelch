from pathlib import Path

import pytest

from squelch.experiments.campaign import (
    CampaignConfigError,
    load_campaign,
    plan_runs,
)
from squelch.experiments.tasks import load_task_manifest
from squelch.skills.loader import load_inventory

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
CAMPAIGN = FIXTURES / "campaigns" / "offline-demo.yaml"


@pytest.fixture(scope="module")
def planned():
    cfg = load_campaign(CAMPAIGN)
    fixtures = load_task_manifest(cfg.dataset_manifest, cfg.graders_root,
                                  environment_image="local:test")
    skills = load_inventory(cfg.skills_root)
    specs = plan_runs(cfg, fixtures, skills, study_id="s1",
                      environment_identity="local:test")
    return cfg, specs


def test_plan_covers_full_grid(planned):
    cfg, specs = planned
    assert len(specs) == 4 * 2 * 1  # tasks x conditions x repetitions
    keys = {(s.task.task_id, s.condition_id, s.repetition) for s in specs}
    assert len(keys) == len(specs)


def test_plan_is_deterministic(planned):
    cfg, specs = planned
    fixtures = load_task_manifest(cfg.dataset_manifest, cfg.graders_root,
                                  environment_image="local:test")
    skills = load_inventory(cfg.skills_root)
    again = plan_runs(cfg, fixtures, skills, study_id="s1",
                      environment_identity="local:test")
    assert [(s.run_id, s.task.task_id, s.condition_id) for s in specs] == \
           [(s.run_id, s.task.task_id, s.condition_id) for s in again]


def test_conditions_interleaved_within_blocks(planned):
    """Condition order must vary across blocks, not be a fixed sequence."""
    cfg, specs = planned
    orders = []
    block: list[str] = []
    current_task = None
    for s in specs:
        if s.task.task_id != current_task:
            if block:
                orders.append(tuple(block))
            block = []
            current_task = s.task.task_id
        block.append(s.condition_id)
    orders.append(tuple(block))
    assert len(set(orders)) > 1, f"all blocks had identical order: {orders[0]}"


def test_skill_hashes_recorded_in_collection(planned):
    cfg, specs = planned
    with_skill = [s for s in specs if s.condition_id == "skill"]
    assert all(len(s.collection.ordered_skill_hashes) == 1 for s in with_skill)
    without = [s for s in specs if s.condition_id == "none"]
    assert all(s.collection.ordered_skill_hashes == [] for s in without)


def test_unknown_skill_rejected(tmp_path, planned):
    cfg, _ = planned
    fixtures = load_task_manifest(cfg.dataset_manifest, cfg.graders_root,
                                  environment_image="local:test")
    with pytest.raises(CampaignConfigError, match="unknown skill"):
        plan_runs(cfg, fixtures, {}, study_id="s1", environment_identity="local:test")


def test_duplicate_condition_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '1'\nname: bad\nbackend: scripted\n"
        "dataset: {manifest: ../tasks/development.yaml}\n"
        "conditions:\n  - {id: a, skills: []}\n  - {id: a, skills: []}\n"
        "repetitions: 1\nschedule_seed: 1\n"
    )
    with pytest.raises(CampaignConfigError, match="duplicate condition"):
        load_campaign(bad)


def test_phase3_policies_rejected_for_now(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '1'\nname: bad\nbackend: scripted\n"
        "dataset: {manifest: ../tasks/development.yaml}\n"
        "conditions:\n  - {id: a, skills: [], policy: isolated}\n"
        "repetitions: 1\nschedule_seed: 1\n"
    )
    with pytest.raises(CampaignConfigError, match="Phase 3"):
        load_campaign(bad)


def test_unsupported_schema_version_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '99'\nname: bad\nbackend: scripted\n"
        "dataset: {manifest: x}\nconditions: [{id: a, skills: []}]\n"
        "repetitions: 1\nschedule_seed: 1\n"
    )
    with pytest.raises(Exception, match="schema_version"):
        load_campaign(bad)
