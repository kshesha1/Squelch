"""Tool broker (spec §5.3).

Minimal tools with structured schemas, explicit size limits, normalized
paths. All file operations stay inside the workspace: absolute paths,
``..`` components, and symlink traversal are rejected. ``run_checks``
takes an allowlisted public check ID from the task manifest, never an
arbitrary shell command; the command executes in the task execution
environment, not on the host shell.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from squelch.sandbox.envs import ExecutionEnvironment
from squelch.schemas import CheckSpec, ResourceLimits


class ToolError(ValueError):
    """Invalid tool input. Returned to the model as an error tool result."""


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "list_files",
        "description": "List files in the task workspace, relative paths, recursive.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the workspace by relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "Write a UTF-8 text file in the workspace by relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_checks",
        "description": "Run a public development check by its ID and return its output.",
        "input_schema": {
            "type": "object",
            "properties": {"check_id": {"type": "string"}},
            "required": ["check_id"],
            "additionalProperties": False,
        },
    },
]


def _validate_relative(path_str: str) -> PurePosixPath:
    if not path_str or path_str.strip() != path_str:
        raise ToolError(f"invalid path: {path_str!r}")
    p = PurePosixPath(path_str)
    if p.is_absolute():
        raise ToolError(f"absolute paths are not permitted: {path_str}")
    if any(part in ("..", "") for part in p.parts):
        raise ToolError(f"path traversal is not permitted: {path_str}")
    return p


class ToolBroker:
    def __init__(
        self,
        workspace: Path,
        *,
        env: ExecutionEnvironment,
        checks: list[CheckSpec],
        limits: ResourceLimits,
    ):
        self.workspace = Path(workspace).resolve()
        self.env = env
        self.checks = {c.check_id: c for c in checks if c.public}
        self.limits = limits

    # -- path safety --------------------------------------------------------

    def _resolve(self, path_str: str, *, for_write: bool) -> Path:
        rel = _validate_relative(path_str)
        target = self.workspace / rel
        # Walk each existing ancestor to refuse symlink traversal.
        probe = self.workspace
        for part in rel.parts:
            probe = probe / part
            if probe.is_symlink():
                raise ToolError(f"symlink traversal is not permitted: {path_str}")
            if not probe.exists():
                break
        resolved_parent = target.parent.resolve()
        if resolved_parent != self.workspace and self.workspace not in resolved_parent.parents:
            raise ToolError(f"path escapes workspace: {path_str}")
        if not for_write and not target.exists():
            raise ToolError(f"file not found: {path_str}")
        return target

    # -- tools --------------------------------------------------------------

    def list_files(self) -> str:
        rels = sorted(
            p.relative_to(self.workspace).as_posix()
            for p in self.workspace.rglob("*")
            if p.is_file()
        )
        return "\n".join(rels) if rels else "(empty workspace)"

    def read_file(self, path: str) -> str:
        target = self._resolve(path, for_write=False)
        if not target.is_file():
            raise ToolError(f"not a regular file: {path}")
        if target.stat().st_size > self.limits.max_file_bytes:
            raise ToolError(
                f"file exceeds read limit of {self.limits.max_file_bytes} bytes: {path}"
            )
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ToolError(f"file is not valid UTF-8: {path}") from exc

    def write_file(self, path: str, content: str) -> str:
        if len(content.encode("utf-8")) > self.limits.max_file_bytes:
            raise ToolError(f"content exceeds write limit of {self.limits.max_file_bytes} bytes")
        target = self._resolve(path, for_write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {path}"

    def run_checks(self, check_id: str) -> str:
        spec = self.checks.get(check_id)
        if spec is None:
            raise ToolError(
                f"unknown or non-public check_id: {check_id!r}; "
                f"available: {sorted(self.checks)}"
            )
        result = self.env.run(
            spec.cmd, workspace=self.workspace, timeout_seconds=spec.timeout_seconds
        )
        status = "TIMEOUT" if result.timed_out else f"exit={result.exit_code}"
        return (
            f"[{check_id}] {status}\n--- stdout ---\n{result.stdout}"
            f"\n--- stderr ---\n{result.stderr}"
        )

    # -- dispatch ------------------------------------------------------------

    def dispatch(self, name: str, tool_input: dict[str, Any]) -> str:
        if name == "list_files":
            return self.list_files()
        if name == "read_file":
            return self.read_file(str(tool_input.get("path", "")))
        if name == "write_file":
            return self.write_file(
                str(tool_input.get("path", "")), str(tool_input.get("content", ""))
            )
        if name == "run_checks":
            return self.run_checks(str(tool_input.get("check_id", "")))
        raise ToolError(f"unknown tool: {name}")
