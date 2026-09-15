"""Execution environments for task code.

Two implementations:

- :class:`DockerEnv` — the spec's task container contract (§5.3): no
  network, non-root, dropped capabilities, no-new-privileges, read-only
  root, bounded writable workspace and tmp, resource limits.
- :class:`LocalEnv` — a subprocess runner for scripted/offline development
  and CI machines without Docker. It is NOT a security boundary and every
  record produced through it carries a ``local:`` environment identity so
  results cannot masquerade as containerized runs. Only authored benign
  fixtures may execute here.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class ExecutionEnvironment(Protocol):
    """Runs a command with a directory mounted/available at a workspace path."""

    def identity(self) -> str: ...

    def run(
        self,
        cmd: list[str],
        *,
        workspace: Path,
        timeout_seconds: int,
        readonly: bool = False,
    ) -> ExecResult: ...


_MAX_CAPTURE = 65536


def _truncate(text: str) -> str:
    if len(text) > _MAX_CAPTURE:
        return text[:_MAX_CAPTURE] + "\n...[truncated]"
    return text


class LocalEnv:
    """Subprocess execution. Not a security boundary; see module docstring."""

    def identity(self) -> str:
        return f"local:python-{platform.python_version()}:{sys.platform}"

    def run(
        self,
        cmd: list[str],
        *,
        workspace: Path,
        timeout_seconds: int,
        readonly: bool = False,
    ) -> ExecResult:
        env = {
            "PATH": os.defpath,
            "HOME": str(workspace),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        # `python` in commands resolves to the interpreter running squelch.
        resolved = [sys.executable if c == "python" else c for c in cmd]
        try:
            proc = subprocess.run(
                resolved,
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return ExecResult(
                proc.returncode, _truncate(proc.stdout), _truncate(proc.stderr), False
            )
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return ExecResult(-1, _truncate(out), _truncate(err), True)


class DockerEnv:
    """Constrained Docker task container per spec §5.3."""

    def __init__(self, image: str, *, memory: str = "512m", cpus: str = "1", pids: int = 128):
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.pids = pids

    def identity(self) -> str:
        return f"docker:{self.image}"

    @staticmethod
    def available() -> bool:
        docker = shutil.which("docker")
        if not docker:
            return False
        try:
            proc = subprocess.run(
                [docker, "info"], capture_output=True, text=True, timeout=15
            )
            return proc.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def run(
        self,
        cmd: list[str],
        *,
        workspace: Path,
        timeout_seconds: int,
        readonly: bool = False,
    ) -> ExecResult:
        mount_mode = "ro" if readonly else "rw"
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--user", "1000:1000",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--pids-limit", str(self.pids),
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "-v", f"{workspace.resolve()}:/workspace:{mount_mode}",
            "-w", "/workspace",
            self.image,
            *cmd,
        ]
        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 30,  # allowance for container start/stop
            )
            return ExecResult(
                proc.returncode, _truncate(proc.stdout), _truncate(proc.stderr), False
            )
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return ExecResult(-1, _truncate(out), _truncate(err), True)
