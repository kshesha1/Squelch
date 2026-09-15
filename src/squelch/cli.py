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
    """Check the local environment: Python, Docker, results directory."""
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
    typer.echo(f"results root: {RESULTS_ROOT.resolve()} "
               f"({'exists' if RESULTS_ROOT.exists() else 'will be created on first run'})")
    typer.echo("live backends: not yet implemented (ticket P1.4); scripted runs are free")


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


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
    backend: str = typer.Option("scripted", "--backend"),
    study_id: str | None = typer.Option(None, "--study-id"),
) -> None:
    """Execute a campaign. Phase 1: scripted backend only, always free."""
    from squelch.experiments.campaign import CampaignConfigError, load_campaign, run_campaign

    try:
        cfg = load_campaign(config)
        if backend != cfg.backend:
            raise CampaignConfigError(
                f"--backend {backend!r} does not match campaign backend {cfg.backend!r}"
            )
        sid, results = run_campaign(cfg, results_root=RESULTS_ROOT / "studies",
                                    study_id=study_id)
    except CampaignConfigError as exc:
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
