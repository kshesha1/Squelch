"""Campaign planner and driver (tickets P1.5 + Ollama live backend).

Responsibilities:

- campaign config parsing and validation (scripted + ollama backends)
- preregistration binding: the prereg file's hash is recorded in the
  study summary before any live run
- run planning: conditions x tasks x repetitions, condition order
  interleaved within task/repetition blocks by the schedule seed (§5.4)
- token-budget ledger: cumulative input/output tokens are checked before
  each dispatch; runs that cannot start are recorded as
  ``not_run_budget``, never silently dropped (§5.6). Local Ollama
  inference is free in USD; token limits still bound wall-clock and
  scope.
- crash-safe resume: completed planned run IDs are reused on
  ``--resume``; a changed config requires a new study (§4.4)
- immutable per-run artifacts + a study summary under the results root
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import yaml

from squelch import __version__
from squelch.backends.protocol import BackendError, ModelBackend
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
    RunStatus,
    StageSpec,
    check_schema_version,
    utc_now,
)
from squelch.skills.loader import SkillPackage, load_inventory

SUPPORTED_BACKENDS = {"scripted", "ollama"}


@dataclass(frozen=True)
class ConditionConfig:
    condition_id: str
    skill_ids: list[str]
    policy: CompositionPolicy


@dataclass(frozen=True)
class BudgetConfig:
    max_total_input_tokens: int | None = None
    max_total_output_tokens: int | None = None


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
    model_id: str | None
    model_host: str
    temperature: float
    seed: int | None
    budget: BudgetConfig
    preregistration: Path | None
    preregistration_hash: str | None


class CampaignConfigError(ValueError):
    pass


def load_campaign(path: Path) -> CampaignConfig:
    path = Path(path)
    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    check_schema_version(str(data["schema_version"]))

    backend = data["backend"]
    if backend not in SUPPORTED_BACKENDS:
        raise CampaignConfigError(
            f"unknown backend: {backend!r}; supported: {sorted(SUPPORTED_BACKENDS)}"
        )

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
    model = data.get("model", {})
    limits = ResourceLimits(
        max_model_calls=runner.get("max_model_calls", 12),
        max_tool_calls=runner.get("max_tool_calls", 30),
        task_timeout_seconds=runner.get("task_timeout_seconds", 180),
        max_output_tokens=model.get("max_output_tokens", 2048),
    )
    model_id = model.get("id")
    if backend == "ollama" and not model_id:
        raise CampaignConfigError("ollama backend requires model.id (e.g. 'qwen3:8b')")

    budget_raw = data.get("budget", {})
    budget = BudgetConfig(
        max_total_input_tokens=budget_raw.get("max_total_input_tokens"),
        max_total_output_tokens=budget_raw.get("max_total_output_tokens"),
    )

    prereg_path = data.get("preregistration")
    prereg_hash = None
    if prereg_path is not None:
        prereg_file = (base / prereg_path).resolve()
        if not prereg_file.is_file():
            raise CampaignConfigError(
                f"declared preregistration file missing: {prereg_file}"
            )
        prereg_hash = hash_text(prereg_file.read_text(encoding="utf-8"))
    elif backend != "scripted":
        raise CampaignConfigError(
            "live campaigns require a 'preregistration' file (spec §5.1); "
            "scripted campaigns may omit it"
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
        model_id=model_id,
        model_host=model.get("host", "http://localhost:11434"),
        temperature=float(model.get("temperature", 0.0)),
        seed=model.get("seed"),
        budget=budget,
        preregistration=(base / prereg_path).resolve() if prereg_path else None,
        preregistration_hash=prereg_hash,
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
    if config.backend == "scripted":
        model = ModelSpec(provider="scripted", requested_model_id="scripted",
                          cost_unknown=False, pricing_reference="free_scripted")
    else:
        model = ModelSpec(
            provider="ollama",
            requested_model_id=config.model_id or "unset",
            parameters={"temperature": config.temperature, "seed": config.seed,
                        "host": config.model_host},
            cost_unknown=False,
            pricing_reference="local_inference_zero_marginal_cost",
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


def plan_text(config: CampaignConfig, fixtures: list[TaskFixture]) -> str:
    """Human-readable plan. Never contacts a model or executes task code."""
    cells = len(fixtures) * len(config.conditions)
    total = cells * config.repetitions
    per_run_in = config.limits.max_model_calls * 8000  # conservative input envelope
    per_run_out = config.limits.max_model_calls * config.limits.max_output_tokens
    lines = [
        f"campaign: {config.name}  backend: {config.backend}"
        + (f"  model: {config.model_id}" if config.model_id else ""),
        f"tasks: {len(fixtures)}  conditions: {len(config.conditions)}  "
        f"repetitions: {config.repetitions}",
        f"cells: {cells}  planned runs: {total}",
        f"per-run limits: {config.limits.max_model_calls} model calls, "
        f"{config.limits.max_tool_calls} tool calls, "
        f"{config.limits.task_timeout_seconds}s timeout, "
        f"{config.limits.max_output_tokens} output tokens/call",
        "conservative token envelope: "
        f"<= {total * per_run_in:,} input, <= {total * per_run_out:,} output tokens",
        "spend: $0 (scripted)" if config.backend == "scripted"
        else "spend: $0 marginal (local ollama inference); token budget "
             f"{config.budget.max_total_input_tokens or 'unlimited'} in / "
             f"{config.budget.max_total_output_tokens or 'unlimited'} out",
        f"preregistration: {config.preregistration_hash or 'none (scripted only)'}",
    ]
    return "\n".join(lines)


def _scripted_backend_for(config: CampaignConfig, spec: RunSpec) -> ScriptedBackend:
    if config.scripted_transcripts is None:
        raise CampaignConfigError(
            "scripted backend requires 'scripted_transcripts' in the campaign config"
        )
    path = config.scripted_transcripts / spec.task.task_id / f"{spec.condition_id}.json"
    if not path.is_file():
        raise CampaignConfigError(f"missing scripted transcript: {path}")
    return ScriptedBackend.from_file(path)


def _make_backend(config: CampaignConfig, spec: RunSpec) -> ModelBackend:
    if config.backend == "scripted":
        return _scripted_backend_for(config, spec)
    from squelch.backends.ollama import OllamaBackend

    return OllamaBackend(
        config.model_id or "unset",
        host=config.model_host,
        temperature=config.temperature,
        seed=config.seed,
    )


class _TokenLedger:
    def __init__(self, budget: BudgetConfig):
        self.budget = budget
        self.input_tokens = 0
        self.output_tokens = 0

    def charge(self, result: RunResult) -> None:
        self.input_tokens += result.usage.input_tokens
        self.output_tokens += result.usage.output_tokens

    def exhausted(self) -> bool:
        b = self.budget
        if b.max_total_input_tokens is not None and self.input_tokens >= b.max_total_input_tokens:
            return True
        return (
            b.max_total_output_tokens is not None
            and self.output_tokens >= b.max_total_output_tokens
        )


def _reusable_result(run_dir: Path, spec: RunSpec) -> RunResult | None:
    """A completed identical planned run may be reused on resume (§4.4)."""
    result_file = run_dir / "result.json"
    spec_file = run_dir / "run_spec.json"
    if not (result_file.is_file() and spec_file.is_file()):
        return None
    try:
        stored_spec = json.loads(spec_file.read_text(encoding="utf-8"))
        planned = spec.model_dump(mode="json")
        # created_at differs between planning passes; identity excludes it
        stored_spec.pop("created_at", None)
        planned.pop("created_at", None)
        if hash_json(stored_spec) != hash_json(planned):
            return None
        result = RunResult.model_validate_json(result_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None  # corrupt artifacts are re-run, not trusted
    if result.status in (RunStatus.COMPLETED, RunStatus.AGENT_LIMIT):
        return result
    return None


def run_campaign(
    config: CampaignConfig,
    *,
    results_root: Path,
    study_id: str | None = None,
    env: ExecutionEnvironment | None = None,
    resume: bool = False,
) -> tuple[str, list[RunResult]]:
    env = env or LocalEnv()
    environment_identity = env.identity()

    fixtures = load_task_manifest(
        config.dataset_manifest, config.graders_root, environment_image=environment_identity
    )
    skills = load_inventory(config.skills_root)
    study_id = study_id or f"{config.name}-{config.config_hash.removeprefix('sha256:')[:8]}"

    study_dir = Path(results_root) / study_id
    existing_summary = study_dir / "study.json"
    if existing_summary.exists():
        prior = json.loads(existing_summary.read_text(encoding="utf-8"))
        if prior.get("config_hash") != config.config_hash:
            raise CampaignConfigError(
                f"study {study_id!r} was created from a different config "
                "(changed manifests require new studies)"
            )
        if not resume:
            raise CampaignConfigError(
                f"study {study_id!r} already exists; results are immutable — "
                "use --resume to fill in missing runs, or pick a new study id"
            )

    specs = plan_runs(
        config, fixtures, skills, study_id=study_id, environment_identity=environment_identity
    )
    fixture_by_id = {f.spec.task_id: f for f in fixtures}
    evaluator = TrustedEvaluator(env, config.graders_root)
    study_dir.mkdir(parents=True, exist_ok=True)

    if config.backend == "ollama":
        from squelch.backends.ollama import OllamaBackend

        probe = OllamaBackend(config.model_id or "unset", host=config.model_host)
        version = probe.server_version()  # raises BackendError when unreachable
        print(f"ollama server {version} at {config.model_host}, model {config.model_id}")

    ledger = _TokenLedger(config.budget)
    results: list[RunResult] = []
    reused = 0
    for spec in specs:
        run_dir = study_dir / "runs" / spec.run_id

        if resume:
            prior_result = _reusable_result(run_dir, spec)
            if prior_result is not None:
                ledger.charge(prior_result)
                results.append(prior_result)
                reused += 1
                continue

        if ledger.exhausted():
            result = RunResult(
                run_id=spec.run_id,
                status=RunStatus.NOT_RUN_BUDGET,
                task_success=None,
                spend_status="token_budget_exhausted",
                error="token budget exhausted before dispatch",
                started_at=utc_now(),
                finished_at=utc_now(),
            )
        else:
            backend = _make_backend(config, spec)
            fixture = fixture_by_id[spec.task.task_id]
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
            ledger.charge(result)

        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run_spec.json").write_text(
            json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
        )
        (run_dir / "result.json").write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
        )
        results.append(result)
        if result.status is RunStatus.INTERRUPTED:
            break  # preserve partial artifacts; remaining runs stay unplanned on disk

    summary = summarize(config, specs, results, environment_identity, reused=reused,
                        ledger=ledger)
    (study_dir / "study.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return study_id, results


def summarize(
    config: CampaignConfig,
    specs: list[RunSpec],
    results: list[RunResult],
    environment_identity: str,
    *,
    reused: int = 0,
    ledger: _TokenLedger | None = None,
) -> dict:
    by_id = {r.run_id: r for r in results}
    cells: dict[tuple[str, str], dict] = {}
    status_counts: dict[str, int] = {}
    for spec in specs:
        r = by_id.get(spec.run_id)
        if r is None:
            continue  # interrupted campaign: unexecuted tail
        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
        key = (spec.task.task_id, spec.condition_id)
        cell = cells.setdefault(
            key, {"task_id": key[0], "condition_id": key[1], "n": 0, "successes": 0,
                  "valid_n": 0, "runs": []}
        )
        cell["n"] += 1
        cell["runs"].append(r.run_id)
        if r.status in (RunStatus.COMPLETED, RunStatus.AGENT_LIMIT):
            cell["valid_n"] += 1
            if r.task_success:
                cell["successes"] += 1
    if config.backend == "scripted":
        disclosure = (
            "Scripted evidence validates the harness program only; it is never a "
            "model-performance claim. Fixtures are authored controls."
        )
    else:
        disclosure = (
            "Screening evidence from local inference on the Squelch runner: "
            "descriptive effects, small N, no confirmation claim. Fixtures are "
            "authored controls; results describe this runner and model only."
        )
    return {
        "schema_version": "1",
        "campaign": config.name,
        "config_hash": config.config_hash,
        "backend": config.backend,
        "model_id": config.model_id,
        "evidence_stage": config.evidence_stage.value,
        "environment": environment_identity,
        "runner_version": __version__,
        "preregistration_hash": config.preregistration_hash,
        "status_counts": status_counts,
        "total_runs": len(results),
        "reused_runs": reused,
        "usage_totals": {
            "input_tokens": ledger.input_tokens if ledger else 0,
            "output_tokens": ledger.output_tokens if ledger else 0,
        },
        "spend_usd": 0.0,
        "generated_at": utc_now().isoformat(),
        "cells": sorted(cells.values(), key=lambda c: (c["task_id"], c["condition_id"])),
        "disclosure": disclosure,
    }


__all__ = [
    "BackendError",
    "BudgetConfig",
    "CampaignConfig",
    "CampaignConfigError",
    "ConditionConfig",
    "load_campaign",
    "plan_runs",
    "plan_text",
    "run_campaign",
    "summarize",
]
