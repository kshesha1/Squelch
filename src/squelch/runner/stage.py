"""Stage scheduler and worker loop (ticket P1.4 foundation).

The scheduler executes a ``stage_plan`` of length *n* as the general case;
Phase 1 plans have length 1. Nothing here special-cases single-stage
execution (spec §3.2). Each stage gets a fresh message context and its own
worker ID; the workspace persists across stages of one run.

Skill exposure in this phase is ``forced``: the prescribed skill bodies are
injected into the stage's system prompt in declared order, and each
exposure is logged as a ``skill_loaded`` event. Skills are never silently
truncated — if the assembled prompt would exceed the declared envelope,
planning fails instead (enforced at prompt-assembly time here).
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from squelch.backends.protocol import (
    BackendError,
    ModelBackend,
    ModelRequest,
    ModelResponse,
    ToolResult,
)
from squelch.hashing import hash_json, hash_text, hash_tree
from squelch.runner.events import EventLog
from squelch.runner.tools import TOOL_SCHEMAS, ToolBroker, ToolError
from squelch.sandbox.envs import ExecutionEnvironment
from squelch.sandbox.evaluator import TrustedEvaluator, task_success
from squelch.schemas import (
    RunResult,
    RunSpec,
    RunStatus,
    StageResult,
    StageSpec,
    TerminationReason,
    TokenUsage,
    utc_now,
)
from squelch.skills.loader import SkillPackage

MAX_SYSTEM_PROMPT_CHARS = 200_000

BASE_SYSTEM_PROMPT = (
    "You are a coding agent working in a sandboxed task workspace. "
    "Use the provided tools to inspect and edit files. "
    "When the task requirements are satisfied, respond with a short final message "
    "instead of calling more tools."
)


class PromptEnvelopeError(ValueError):
    """Assembled instructions exceed the declared input envelope (§5.2)."""


def assemble_system_prompt(stage: StageSpec, skills: dict[str, SkillPackage]) -> str:
    parts = [BASE_SYSTEM_PROMPT]
    for skill_id in stage.exposed_skill_ids:
        pkg = skills[skill_id]
        parts.append(
            f"\n<skill name={pkg.snapshot.name!r}>\n{pkg.body.strip()}\n</skill>"
        )
    prompt = "\n".join(parts)
    if len(prompt) > MAX_SYSTEM_PROMPT_CHARS:
        raise PromptEnvelopeError(
            f"system prompt {len(prompt)} chars exceeds envelope "
            f"{MAX_SYSTEM_PROMPT_CHARS}; never truncate a skill silently"
        )
    return prompt


@dataclass
class StageOutcome:
    result: StageResult
    final_text: str | None


class StageScheduler:
    """Executes every stage of a run's plan against one persistent workspace."""

    def __init__(
        self,
        backend: ModelBackend,
        env: ExecutionEnvironment,
        skills: dict[str, SkillPackage],
        events: EventLog,
    ):
        self.backend = backend
        self.env = env
        self.skills = skills
        self.events = events

    def run_stages(
        self, spec: RunSpec, workspace: Path, task_prompt: str
    ) -> tuple[list[StageResult], TerminationReason]:
        results: list[StageResult] = []
        termination = TerminationReason.FINAL_RESPONSE
        for index, stage in enumerate(spec.stage_plan):
            worker_id = f"worker-{index + 1}"
            outcome = self._run_stage(spec, stage, worker_id, workspace, task_prompt)
            results.append(outcome.result)
            termination = outcome.result.termination_reason
            if termination is not TerminationReason.FINAL_RESPONSE:
                break  # a limit or error in any stage ends the run
        return results, termination

    def _run_stage(
        self,
        spec: RunSpec,
        stage: StageSpec,
        worker_id: str,
        workspace: Path,
        task_prompt: str,
    ) -> StageOutcome:
        missing = [s for s in stage.exposed_skill_ids if s not in self.skills]
        if missing:
            raise KeyError(f"stage {stage.stage_id} references unknown skills: {missing}")

        self.events.emit(
            "stage_started",
            {"stage_id": stage.stage_id, "worker_id": worker_id},
            stage_id=stage.stage_id,
            agent_id=worker_id,
        )
        system = assemble_system_prompt(stage, self.skills)
        for skill_id in stage.exposed_skill_ids:
            pkg = self.skills[skill_id]
            self.events.emit(
                "skill_loaded",
                {
                    "skill_id": skill_id,
                    "package_hash": pkg.snapshot.package_hash,
                    "file": "SKILL.md",
                    "content_hash": hash_text(pkg.body),
                    "reason": "forced",
                },
                stage_id=stage.stage_id,
                agent_id=worker_id,
            )

        broker = ToolBroker(
            workspace,
            env=self.env,
            checks=spec.task.checks,
            limits=stage.limits,
        )
        messages: list[dict] = [{"role": "user", "content": task_prompt}]
        usage = TokenUsage()
        model_calls = 0
        tool_calls = 0
        final_text: str | None = None
        termination = TerminationReason.FINAL_RESPONSE
        deadline = time.monotonic() + stage.limits.task_timeout_seconds

        while True:
            if model_calls >= stage.limits.max_model_calls:
                termination = TerminationReason.MODEL_CALL_LIMIT
                self.events.emit(
                    "limit_reached",
                    {"limit": "max_model_calls", "value": stage.limits.max_model_calls},
                    stage_id=stage.stage_id, agent_id=worker_id,
                )
                break
            if time.monotonic() > deadline:
                termination = TerminationReason.TIMEOUT
                self.events.emit(
                    "limit_reached",
                    {"limit": "task_timeout_seconds",
                     "value": stage.limits.task_timeout_seconds},
                    stage_id=stage.stage_id, agent_id=worker_id,
                )
                break

            request = ModelRequest(
                system=system,
                messages=messages,
                tools=TOOL_SCHEMAS,
                max_output_tokens=stage.limits.max_output_tokens,
                metadata={"run_id": spec.run_id, "stage_id": stage.stage_id},
            )
            self.events.emit(
                "model_request",
                {"call_index": model_calls + 1, "message_count": len(messages)},
                stage_id=stage.stage_id, agent_id=worker_id,
            )
            response: ModelResponse = self.backend.complete(request)
            model_calls += 1
            usage = usage.add(response.usage)
            self.events.emit(
                "model_response",
                {
                    "stop_reason": response.stop_reason,
                    "tool_call_count": len(response.tool_calls),
                    "usage": response.usage.model_dump(),
                },
                stage_id=stage.stage_id, agent_id=worker_id,
            )

            if not response.wants_tools:
                final_text = response.text
                termination = TerminationReason.FINAL_RESPONSE
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {"id": c.tool_call_id, "name": c.name, "input": c.input}
                        for c in response.tool_calls
                    ],
                }
            )
            tool_results: list[ToolResult] = []
            limit_hit = False
            for call in response.tool_calls:
                if tool_calls >= stage.limits.max_tool_calls:
                    termination = TerminationReason.TOOL_CALL_LIMIT
                    self.events.emit(
                        "limit_reached",
                        {"limit": "max_tool_calls", "value": stage.limits.max_tool_calls},
                        stage_id=stage.stage_id, agent_id=worker_id,
                    )
                    limit_hit = True
                    break
                tool_calls += 1
                self.events.emit(
                    "tool_requested",
                    {"tool_call_id": call.tool_call_id, "name": call.name,
                     "input": call.input},
                    stage_id=stage.stage_id, agent_id=worker_id,
                )
                try:
                    output = broker.dispatch(call.name, call.input)
                    is_error = False
                except ToolError as exc:
                    # Invalid tool use is agent behavior, not a harness failure.
                    output = f"tool error: {exc}"
                    is_error = True
                tool_results.append(ToolResult(call.tool_call_id, output, is_error))
                self.events.emit(
                    "tool_completed",
                    {"tool_call_id": call.tool_call_id, "name": call.name,
                     "is_error": is_error, "output_chars": len(output)},
                    stage_id=stage.stage_id, agent_id=worker_id,
                )
                if call.name == "write_file" and not is_error:
                    self.events.emit(
                        "file_written",
                        {"path": call.input.get("path")},
                        stage_id=stage.stage_id, agent_id=worker_id,
                    )
            if limit_hit:
                break
            messages.append(
                {
                    "role": "tool",
                    "content": [
                        {"tool_call_id": r.tool_call_id, "output": r.output,
                         "is_error": r.is_error}
                        for r in tool_results
                    ],
                }
            )

        result = StageResult(
            stage_id=stage.stage_id,
            worker_id=worker_id,
            exposed_skill_ids=list(stage.exposed_skill_ids),
            model_calls=model_calls,
            tool_calls=tool_calls,
            usage=usage,
            handoff_produced=False,  # handoffs arrive with Phase 3 policies
            termination_reason=termination,
        )
        self.events.emit(
            "stage_finished",
            {"stage_id": stage.stage_id,
             "termination_reason": termination.value,
             "model_calls": model_calls, "tool_calls": tool_calls},
            stage_id=stage.stage_id, agent_id=worker_id,
        )
        return StageOutcome(result=result, final_text=final_text)


def execute_run(
    spec: RunSpec,
    *,
    backend: ModelBackend,
    env: ExecutionEnvironment,
    skills: dict[str, SkillPackage],
    task_prompt: str,
    starter_dir: Path,
    evaluator: TrustedEvaluator,
    run_dir: Path,
) -> RunResult:
    """Execute one run end to end: fresh workspace, stages, trusted evaluation.

    The workspace is reset from the starter tree for every run (§5.4).
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    workspace = run_dir / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(starter_dir, workspace)

    events = EventLog(run_dir / "events.jsonl", spec.run_id)
    started = utc_now()
    events.emit(
        "run_started",
        {
            "condition_id": spec.condition_id,
            "task_id": spec.task.task_id,
            "repetition": spec.repetition,
            "backend": backend.name,
            "environment": env.identity(),
            "stage_count": len(spec.stage_plan),
        },
    )

    scheduler = StageScheduler(backend, env, skills, events)
    try:
        stage_results, termination = scheduler.run_stages(spec, workspace, task_prompt)
    except BackendError as exc:
        events.emit("run_error", {"error": str(exc), "kind": "backend"})
        return RunResult(
            run_id=spec.run_id,
            status=RunStatus.INVALID,
            task_success=None,
            termination_reason=TerminationReason.BACKEND_ERROR,
            error=str(exc),
            trace_path=str(run_dir / "events.jsonl"),
            started_at=started,
            finished_at=utc_now(),
        )
    except KeyboardInterrupt:
        events.emit("run_error", {"error": "operator interrupt", "kind": "interrupt"})
        return RunResult(
            run_id=spec.run_id,
            status=RunStatus.INTERRUPTED,
            task_success=None,
            termination_reason=TerminationReason.OPERATOR_INTERRUPT,
            error="operator interrupt",
            trace_path=str(run_dir / "events.jsonl"),
            started_at=started,
            finished_at=utc_now(),
        )

    usage = TokenUsage()
    for sr in stage_results:
        usage = usage.add(sr.usage)

    # Trusted evaluation runs even for agent_limit runs: the endpoint counts
    # them as non-success, but the workspace state is still recorded.
    try:
        assertions, evaluated_hash = evaluator.evaluate(spec.task, workspace)
    except Exception as exc:  # evaluator failure -> invalid, never a fake fail
        events.emit("run_error", {"error": str(exc), "kind": "evaluator"})
        return RunResult(
            run_id=spec.run_id,
            status=RunStatus.INVALID,
            task_success=None,
            usage=usage,
            stage_results=stage_results,
            termination_reason=termination,
            error=f"evaluator failure: {exc}",
            trace_path=str(run_dir / "events.jsonl"),
            started_at=started,
            finished_at=utc_now(),
        )

    success = task_success(assertions)
    if termination is not TerminationReason.FINAL_RESPONSE:
        status = RunStatus.AGENT_LIMIT
        success = False  # limit runs count as non-success for the task endpoint
    else:
        status = RunStatus.COMPLETED

    events.emit(
        "evaluation_completed",
        {
            "task_success": success,
            "assertions": [a.model_dump() for a in assertions],
        },
    )
    result = RunResult(
        run_id=spec.run_id,
        status=status,
        task_success=success,
        assertions=assertions,
        usage=usage,
        spend_status="free_scripted" if backend.name == "scripted" else "cost_unknown",
        artifact_hashes={
            "final_workspace": hash_tree(workspace),
            "evaluated_outputs": evaluated_hash,
            "run_spec": hash_json(spec.model_dump(mode="json")),
        },
        trace_path=str(run_dir / "events.jsonl"),
        termination_reason=termination,
        stage_results=stage_results,
        started_at=started,
        finished_at=utc_now(),
    )
    events.emit("run_finished", {"status": status.value, "task_success": success})
    return result
