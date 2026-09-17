"""Squelch CLI (target contract in spec §4.4; implemented subset only)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import typer

from squelch import __version__

app = typer.Typer(
    name="squelch",
    help="Experimental laboratory for agent-skill composition.",
    no_args_is_help=True,
)

RESULTS_ROOT = Path(".squelch")

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_INVALID = 2
EXIT_INSUFFICIENT = 3


@app.command()
def version() -> None:
    """Print the squelch version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Check the local environment: Python, Docker, Ollama, results directory."""
    from squelch.backends.ollama import DEFAULT_HOST, OllamaBackend
    from squelch.backends.protocol import BackendError
    from squelch.sandbox.envs import DockerEnv

    typer.echo(f"squelch {__version__}")
    typer.echo(f"python: {sys.version.split()[0]} ({sys.executable})")
    docker_cli = shutil.which("docker")
    if docker_cli and DockerEnv.available():
        typer.echo("docker: available (task containers usable)")
    elif docker_cli:
        typer.echo("docker: CLI found but daemon unreachable — container runs unavailable")
    else:
        typer.echo("docker: not found — only the local (non-isolating) environment is usable")
    try:
        v = OllamaBackend("probe").server_version()
        typer.echo(f"ollama: server {v} reachable at {DEFAULT_HOST} (live local runs usable)")
    except BackendError:
        typer.echo(
            f"ollama: not reachable at {DEFAULT_HOST} — install ollama and run "
            "`ollama serve` (plus `ollama pull <model>`) for live local runs"
        )
    typer.echo(f"results root: {RESULTS_ROOT.resolve()} "
               f"({'exists' if RESULTS_ROOT.exists() else 'will be created on first run'})")


@app.command()
def validate(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Validate a campaign config, its task manifest, and its skills."""
    from squelch.experiments.campaign import CampaignConfigError, load_campaign
    from squelch.experiments.tasks import load_task_manifest
    from squelch.skills.loader import SkillValidationError, load_inventory

    try:
        cfg = load_campaign(config)
        fixtures = load_task_manifest(
            cfg.dataset_manifest, cfg.graders_root, environment_image="validate"
        )
        skills = load_inventory(cfg.skills_root)
        for cond in cfg.conditions:
            for sid in cond.skill_ids:
                if sid not in skills:
                    raise CampaignConfigError(
                        f"condition {cond.condition_id!r} references unknown skill {sid!r}"
                    )
    except (CampaignConfigError, SkillValidationError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"invalid: {exc}", err=True)
        raise typer.Exit(EXIT_INVALID) from exc
    typer.echo(f"campaign {cfg.name!r}: {len(cfg.conditions)} conditions, "
               f"{len(fixtures)} tasks, {cfg.repetitions} repetitions, "
               f"{len(cfg.conditions) * len(fixtures) * cfg.repetitions} planned runs")
    typer.echo(f"skills available: {sorted(skills)}")
    typer.echo(f"config hash: {cfg.config_hash}")
    if cfg.preregistration_hash:
        typer.echo(f"preregistration hash: {cfg.preregistration_hash}")


@app.command()
def plan(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Print the run plan and token envelope. Never contacts a model."""
    from squelch.experiments.campaign import CampaignConfigError, load_campaign, plan_text
    from squelch.experiments.tasks import load_task_manifest

    try:
        cfg = load_campaign(config)
        fixtures = load_task_manifest(
            cfg.dataset_manifest, cfg.graders_root, environment_image="plan"
        )
    except (CampaignConfigError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"invalid: {exc}", err=True)
        raise typer.Exit(EXIT_INVALID) from exc
    typer.echo(plan_text(cfg, fixtures))


@app.command()
def prereg(
    phase: int = typer.Option(..., "--phase"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    """Write a preregistration template. Fill it in and commit BEFORE live runs."""
    import subprocess

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
        ).stdout.strip() or "UNCOMMITTED"
    except (OSError, subprocess.TimeoutExpired):
        commit = "UNKNOWN"
    template = f"""schema_version: '1'
phase_id: 'phase-{phase:02d}'
# Declared BEFORE any live campaign in this phase. Analyses not listed
# here are labeled exploratory in every report and post (spec §5.1).
hypotheses:
  - 'FILL IN: e.g. skill X raises task success on family Y vs no-skill baseline'
primary_endpoint: task_success
minimum_useful_effect_pp: 10
planned_n: 24
n_rationale: 'FILL IN: e.g. 4 tasks x 2 conditions x 3 repetitions; screening only'
analysis_method: 'descriptive rates with Wilson intervals; screening stage'
exclusion_rules:
  - 'runs with status invalid are excluded from the valid denominator and reported'
commit_hash: '{commit}'
created_utc: 'FILL IN before committing'
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        typer.echo(f"refusing to overwrite existing preregistration: {out}", err=True)
        raise typer.Exit(EXIT_INVALID)
    out.write_text(template, encoding="utf-8")
    typer.echo(f"preregistration template written: {out}")
    typer.echo("Fill it in, commit it, then reference it from the campaign config.")


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
    backend: str = typer.Option("scripted", "--backend"),
    study_id: str | None = typer.Option(None, "--study-id"),
    resume: bool = typer.Option(False, "--resume",
                                help="Reuse completed identical planned runs."),
) -> None:
    """Execute a campaign. Backends: scripted (free), ollama (local inference)."""
    from squelch.backends.protocol import BackendError
    from squelch.experiments.campaign import CampaignConfigError, load_campaign, run_campaign

    try:
        cfg = load_campaign(config)
        if backend != cfg.backend:
            raise CampaignConfigError(
                f"--backend {backend!r} does not match campaign backend {cfg.backend!r}"
            )
        sid, results = run_campaign(cfg, results_root=RESULTS_ROOT / "studies",
                                    study_id=study_id, resume=resume)
    except (CampaignConfigError, BackendError) as exc:
        typer.echo(f"invalid: {exc}", err=True)
        raise typer.Exit(EXIT_INVALID) from exc
    statuses: dict[str, int] = {}
    for r in results:
        statuses[r.status.value] = statuses.get(r.status.value, 0) + 1
    typer.echo(f"study: {sid}")
    typer.echo(f"runs: {len(results)}  status counts: {statuses}")
    typer.echo(f"artifacts: {RESULTS_ROOT / 'studies' / sid}")
    if statuses.get("invalid"):
        raise typer.Exit(EXIT_INVALID)
    if statuses.get("not_run_budget"):
        typer.echo("note: some runs were not started (token budget); "
                   "the study is incomplete, never 'successful by omission'")


@app.command()
def replay(
    study_id: str = typer.Argument(...),
    out_study: str | None = typer.Option(None, "--out-study",
                                         help="Derived study id (default: <study>-reanalyzed)."),
) -> None:
    """Re-analyze a stored study offline. Contacts nothing; re-runs nothing.

    Re-derives each run's status and termination from its recorded events
    using the current classification rules, and writes a NEW derived study.
    The source study is never modified.
    """
    from squelch.analysis.replay import ReplayError, replay_study

    source = RESULTS_ROOT / "studies" / study_id
    if not (source / "study.json").exists():
        typer.echo(f"invalid: no study summary at {source}/study.json", err=True)
        raise typer.Exit(EXIT_INVALID)
    dest = RESULTS_ROOT / "studies" / (out_study or f"{study_id}-reanalyzed")
    try:
        summary = replay_study(source, dest)
    except ReplayError as exc:
        typer.echo(f"invalid: {exc}", err=True)
        raise typer.Exit(EXIT_INVALID) from exc
    changed = summary["reclassified_runs"]
    typer.echo(f"derived study: {dest.name}")
    typer.echo(f"runs re-analyzed: {summary['total_runs']}  "
               f"reclassified: {len(changed)}")
    for c in changed:
        typer.echo(f"  {c['run_id']}: {c['was']['status']}/"
                   f"{c['was']['termination_reason']} -> "
                   f"{c['now']['status']}/{c['now']['termination_reason']}")
    typer.echo(f"status counts: {summary['status_counts']}")
    typer.echo("no model was called; grading unchanged")


@app.command()
def report(
    study_id: str = typer.Argument(...),
    out: Path = typer.Option(Path("report.html"), "--out"),
) -> None:
    """Render a self-contained offline HTML report for a study."""
    from squelch.reporting.report import render_study_report

    study_dir = RESULTS_ROOT / "studies" / study_id
    if not (study_dir / "study.json").exists():
        typer.echo(f"invalid: no study summary at {study_dir}/study.json", err=True)
        raise typer.Exit(EXIT_INVALID)
    path = render_study_report(study_dir, out)
    typer.echo(f"report written: {path}")


if __name__ == "__main__":
    app()
