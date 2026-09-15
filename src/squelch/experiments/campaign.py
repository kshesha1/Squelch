"""Minimal campaign driver for the offline scripted path.

This is the seed of ticket P1.5 (budget reservation, crash-safe resume,
and preregistration binding are still to come — see docs/decisions).
What exists now:

- campaign config parsing and validation
- run planning: conditions x tasks x repetitions, condition order
  interleaved within task/repetition blocks by the schedule seed (§5.4)
- execution against the scripted backend with per-run transcripts
- immutable per-run artifacts + a study summary under the results root
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import yaml

from squelch import __version__
from squelch.backends.protocol import ModelBackend
from squelch.backends.scripted import ScriptedBackend
from squelch.experiments.tasks import TaskFixture, load_task_manifest
from squelch.hashing import hash_json, hash_text
from squelch.runner.stage import BASE_SYSTEM_PROMPT, execute_run
from squelch.runner.tools import TOOL_SCHEMAS
from squelch.sandbox.envs import ExecutionEnvironment, LocalEnv
from squelch.sandbox.evaluator import TrustedEvaluator
from squelch.schemas import (
    CollectionSnapshot,
    CompositionPolicy,
    EvidenceStage,
    LoadingMode,
    ModelSpec,
    ResourceLimits,
    RunResult,
    RunSpec,
    StageSpec,
    check_schema_version,
)
from squelch.skills.loader import SkillPackage, load_inventory


@dataclass(frozen=True)
class ConditionConfig:
    condition_id: str
    skill_ids: list[str]
    policy: CompositionPolicy


@dataclass(frozen=True)
class CampaignConfig:
    name: str
    backend: str
    dataset_manifest: Path
    conditions: list[ConditionConfig]
    repetitions: int
    schedule_seed: int
    skills_root: Path
    graders_root: Path
    limits: ResourceLimits
    evidence_stage: EvidenceStage
    scripted_transcripts: Path | None
    config_hash: str


class CampaignConfigError(ValueError):
    pass


def load_campaign(path: Path) -> CampaignConfig:
    path = Path(path)
    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    check_schema_version(str(data["schema_version"]))

    backend = data["backend"]
    if backend not in {"scripted", "anthropic"}:
        raise CampaignConfigError(f"unknown backend: {backend!r}")

    conditions = []
    seen = set()
    for c in data["conditions"]:
        cid = c["id"]
        if cid in seen:
            raise CampaignConfigError(f"duplicate condition id: {cid}")
        seen.add(cid)
        policy = CompositionPolicy(c.get("policy", "shared"))
        if policy is not CompositionPolicy.SHARED:
            raise CampaignConfigError(
                f"composition policy {policy.value!r} arrives in Phase 3; Phase 1 supports shared"
            )
        conditions.append(
            ConditionConfig(condition_id=cid, skill_ids=list(c.get("skills", [])), policy=policy)
        )
    if not conditions:
        raise CampaignConfigError("campaign declares no conditions")

    base = path.parent
    runner = data.get("runner", {})
    limits = ResourceLimits(
        max_model_calls=runner.get("max_model_calls", 12),
        max_tool_calls=runner.get("max_tool_calls", 30),
        task_timeout_seconds=runner.get("task_timeout_seconds", 180),
        max_output_tokens=data.get("model", {}).get("max_output_tokens", 2048),
    )
    transcripts = data.get("scripted_transcripts")
    return CampaignConfig(
        name=data["name"],
        backend=backend,
        dataset_manifest=(base / data["dataset"]["manifest"]).resolve(),
        conditions=conditions,
        repetitions=int(data["repetitions"]),
        schedule_seed=int(data["schedule_seed"]),
        skills_root=(base / data.get("skills_root", "../skills")).resolve(),
        graders_root=(base / data.get("graders_root", "../graders")).resolve(),
        limits=limits,
        evidence_stage=EvidenceStage(data.get("analysis", {}).get("stage", "screening")),
        scripted_transcripts=(base / transcripts).resolve() if transcripts else None,
        config_hash=hash_text(raw_text),
    )


def plan_runs(
    config: CampaignConfig,
    fixtures: list[TaskFixture],
    skills: dict[str, SkillPackage],
    *,
    study_id: str,
    environment_identity: str,
) -> list[RunSpec]:
    """Deterministic run plan: interleave condition order per task/repetition block."""
    for cond in config.conditions:
        for sid in cond.skill_ids:
            if sid not in skills:
                raise CampaignConfigError(
                    f"condition {cond.condition_id!r} references unknown skill {sid!r}; "
                    f"available: {sorted(skills)}"
                )

    rng = random.Random(config.schedule_seed)
    tool_schema_hash = hash_json(TOOL_SCHEMAS)
    system_prompt_hash = hash_text(BASE_SYSTEM_PROMPT)
    model = ModelSpec(
        provider=config.backend,
        requested_model_id="scripted" if config.backend == "scripted" else "unset",
        cost_unknown=config.backend != "scripted",
    )

    specs: list[RunSpec] = []
    counter = 0
    for fixture in fixtures:
        for rep in range(1, config.repetitions + 1):
            block = list(config.conditions)
            rng.shuffle(block)
            for cond in block:
                counter += 1
                ordered_hashes = [skills[s].snapshot.package_hash for s in cond.skill_ids]
                collection = CollectionSnapshot(
                    ordered_skill_hashes=ordered_hashes,
                    composition_policy=cond.policy,
                    policy_hash=hash_json({"policy": cond.policy.value}),
                    loading_mode=LoadingMode.FORCED,
                    system_prompt_hash=system_prompt_hash,
                    tool_schema_hash=tool_schema_hash,
                    runner_version=__version__,
                )
                stage = StageSpec(
                    stage_id="implement",
                    exposed_skill_ids=list(cond.skill_ids),
                    limits=config.limits,
                )
                task = fixture.spec.model_copy(
                    update={"environment_image": environment_identity}
                )
                specs.append(
                    RunSpec(
                        run_id=f"{study_id}-r{counter:04d}",
                        study_id=study_id,
                        condition_id=cond.condition_id,
                        task=task,
                        collection=collection,
                        model=model,
                        repetition=rep,
                        schedule_seed=config.schedule_seed,
                        stage_plan=[stage],
                    )
                )
    return specs


def _scripted_backend_for(
    config: CampaignConfig, spec: RunSpec
) -> ScriptedBackend:
    if config.scripted_transcripts is None:
        raise CampaignConfigError(
            "scripted backend requires 'scripted_transcripts' in the campaign config"
        )
    path = config.scripted_transcripts / spec.task.task_id / f"{spec.condition_id}.json"
    if not path.is_file():
        raise CampaignConfigError(f"missing scripted transcript: {path}")
    return ScriptedBackend.from_file(path)


def run_campaign(
    config: CampaignConfig,
    *,
    results_root: Path,
    study_id: str | None = None,
    env: ExecutionEnvironment | None = None,
) -> tuple[str, list[RunResult]]:
    """Execute a campaign. Phase 1 supports the scripted backend only."""
    if config.backend != "scripted":
        raise CampaignConfigError(
            "live backends land with ticket P1.4; only 'scripted' is runnable today"
        )
    env = env or LocalEnv()
    environment_identity = env.identity()

    fixtures = load_task_manifest(
        config.dataset_manifest, config.graders_root, environment_image=environment_identity
    )
    skills = load_inventory(config.skills_root)
    study_id = study_id or f"{config.name}-{config.config_hash.removeprefix('sha256:')[:8]}"

    specs = plan_runs(
        config, fixtures, skills, study_id=study_id, environment_identity=environment_identity
    )
    fixture_by_id = {f.spec.task_id: f for f in fixtures}
    evaluator = TrustedEvaluator(env, config.graders_root)

    study_dir = Path(results_root) / study_id
    study_dir.mkdir(parents=True, exist_ok=True)
    results: list[RunResult] = []
    for spec in specs:
        backend: ModelBackend = _scripted_backend_for(config, spec)
        fixture = fixture_by_id[spec.task.task_id]
        run_dir = study_dir / "runs" / spec.run_id
        result = execute_run(
            spec,
            backend=backend,
            env=env,
            skills=skills,
            task_prompt=fixture.prompt,
            starter_dir=fixture.starter_dir,
            evaluator=evaluator,
            run_dir=run_dir,
        )
        (run_dir / "run_spec.json").write_text(
            json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
        )
        (run_dir / "result.json").write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
        )
        results.append(result)

    summary = summarize(config, specs, results, environment_identity)
    (study_dir / "study.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return study_id, results


def summarize(
    config: CampaignConfig,
    specs: list[RunSpec],
    results: list[RunResult],
    environment_identity: str,
) -> dict:
    by_id = {r.run_id: r for r in results}
    cells: dict[tuple[str, str], dict] = {}
    status_counts: dict[str, int] = {}
    for spec in specs:
        r = by_id[spec.run_id]
        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
        key = (spec.task.task_id, spec.condition_id)
        cell = cells.setdefault(
            key, {"task_id": key[0], "condition_id": key[1], "n": 0, "successes": 0,
                  "valid_n": 0, "runs": []}
        )
        cell["n"] += 1
        cell["runs"].append(r.run_id)
        if r.status.value in ("completed", "agent_limit"):
            cell["valid_n"] += 1
            if r.task_success:
                cell["successes"] += 1
    return {
        "schema_version": "1",
        "campaign": config.name,
        "config_hash": config.config_hash,
        "backend": config.backend,
        "evidence_stage": config.evidence_stage.value,
        "environment": environment_identity,
        "runner_version": __version__,
        "status_counts": status_counts,
        "total_runs": len(results),
        "cells": sorted(cells.values(), key=lambda c: (c["task_id"], c["condition_id"])),
        "disclosure": (
            "Scripted evidence validates the harness program only; it is never a "
            "model-performance claim. Fixtures are authored controls."
            if config.evidence_stage is EvidenceStage.SCRIPTED
            else "Screening evidence: descriptive effects, small N, no confirmation claim."
        ),
    }
