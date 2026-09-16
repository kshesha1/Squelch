"""Data contracts for Squelch (spec §4).

All persisted records carry ``schema_version``, stable IDs, and UTC
timestamps. Unknown enum values and incompatible schema versions are
rejected explicitly at load time via :func:`check_schema_version`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from squelch import SCHEMA_VERSION

SUPPORTED_SCHEMA_VERSIONS = {SCHEMA_VERSION}


class SchemaVersionError(ValueError):
    pass


def check_schema_version(value: str) -> str:
    if value not in SUPPORTED_SCHEMA_VERSIONS:
        raise SchemaVersionError(
            f"unsupported schema_version {value!r}; supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    return value


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VersionedRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------


class RunStatus(StrEnum):
    """Execution status, deliberately separate from task quality (§4.3)."""

    COMPLETED = "completed"        # agent stopped normally; may pass or fail the task
    AGENT_LIMIT = "agent_limit"    # exhausted declared calls/time/output budget
    INVALID = "invalid"            # harness/sandbox/provider infrastructure failure
    NOT_RUN_BUDGET = "not_run_budget"
    INTERRUPTED = "interrupted"


class EvidenceStage(StrEnum):
    SCRIPTED = "scripted"          # validates the program, never a model-performance claim
    SCREENING = "screening"
    CONFIRMATION = "confirmation"
    EXTERNAL_REPLICATION = "external_replication"


class LoadingMode(StrEnum):
    FORCED = "forced"
    DISCOVERY = "discovery"


class CompositionPolicy(StrEnum):
    SHARED = "shared"
    SHARED_MATCHED_PROMPT = "shared_matched_prompt"
    PHASED = "phased"
    ISOLATED = "isolated"


class TaskSplit(StrEnum):
    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class TerminationReason(StrEnum):
    FINAL_RESPONSE = "final_response"
    MODEL_CALL_LIMIT = "model_call_limit"
    TOOL_CALL_LIMIT = "tool_call_limit"
    TIMEOUT = "timeout"
    BACKEND_ERROR = "backend_error"
    HARNESS_ERROR = "harness_error"
    OPERATOR_INTERRUPT = "operator_interrupt"


# --------------------------------------------------------------------------
# Core entities (§4.1)
# --------------------------------------------------------------------------


class SkillSnapshot(VersionedRecord):
    skill_id: str
    package_hash: str
    name: str
    description: str
    files: dict[str, str]  # relative POSIX path -> sha256:... of exact bytes
    source_url: str | None = None
    license: str | None = None
    # Unknown optional metadata is preserved as data, never as execution authority.
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceLimits(StrictModel):
    max_model_calls: int = 12
    max_tool_calls: int = 30
    task_timeout_seconds: int = 180
    max_output_tokens: int = 2048
    max_file_bytes: int = 262_144  # per tool read/write payload


class CheckSpec(StrictModel):
    check_id: str
    cmd: list[str]
    public: bool = True  # public dev checks may be agent-visible via run_checks
    timeout_seconds: int = 60


class TaskSpec(VersionedRecord):
    task_id: str
    family_id: str
    split: TaskSplit
    prompt_hash: str
    starter_tree_hash: str
    environment_image: str  # image digest/tag, or "local:<python-version>" for LocalEnv
    grader_hash: str
    allowed_outputs: list[str]  # glob patterns of files the grader will consider
    checks: list[CheckSpec] = Field(default_factory=list)
    limits: ResourceLimits = Field(default_factory=ResourceLimits)


class ModelSpec(VersionedRecord):
    provider: str
    requested_model_id: str
    reported_model_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    sdk_version: str | None = None
    pricing_reference: str | None = None  # None means cost_unknown
    cost_unknown: bool = True


class CollectionSnapshot(VersionedRecord):
    ordered_skill_hashes: list[str]
    composition_policy: CompositionPolicy
    policy_hash: str
    loading_mode: LoadingMode
    system_prompt_hash: str
    tool_schema_hash: str
    runner_version: str


class StageSpec(StrictModel):
    stage_id: str
    exposed_skill_ids: list[str]  # forced exposure, in declared order
    limits: ResourceLimits = Field(default_factory=ResourceLimits)


class RunSpec(VersionedRecord):
    run_id: str
    study_id: str
    condition_id: str
    task: TaskSpec
    collection: CollectionSnapshot
    model: ModelSpec
    repetition: int
    schedule_seed: int
    stage_plan: list[StageSpec]
    created_at: datetime = Field(default_factory=utc_now)


class TokenUsage(StrictModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )


class StageResult(VersionedRecord):
    stage_id: str
    worker_id: str
    exposed_skill_ids: list[str]
    model_calls: int
    tool_calls: int
    usage: TokenUsage
    handoff_produced: bool
    termination_reason: TerminationReason


class AssertionOutcome(StrictModel):
    assertion_id: str
    passed: bool
    mandatory: bool = True
    detail: str = ""


class RunResult(VersionedRecord):
    run_id: str
    status: RunStatus
    task_success: bool | None  # None when status is not `completed`/`agent_limit`
    assertions: list[AssertionOutcome] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    spend_usd: float | None = None
    spend_status: str = "cost_unknown"
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    trace_path: str | None = None
    termination_reason: TerminationReason | None = None
    stage_results: list[StageResult] = Field(default_factory=list)
    # workspace file changes relative to the starter tree, as "A path" /
    # "M path" / "D path" lines; full diffs live in the diff.patch artifact
    changed_files: list[str] = Field(default_factory=list)
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Comparison(VersionedRecord):
    comparison_id: str
    baseline_ids: list[str]
    candidate_ids: list[str]
    estimand: str
    analysis_unit: str
    effect_estimate: float | None
    uncertainty_method: str
    interval: tuple[float, float] | None
    exclusions: list[str] = Field(default_factory=list)
    evidence_stage: EvidenceStage
    preregistration_hash: str | None = None


class Preregistration(VersionedRecord):
    phase_id: str
    hypotheses: list[str]
    primary_endpoint: str
    minimum_useful_effect: float
    planned_n: int
    n_rationale: str
    analysis_method: str
    exclusion_rules: list[str]
    commit_hash: str
    created_at: datetime = Field(default_factory=utc_now)


# --------------------------------------------------------------------------
# Events (§4.2)
# --------------------------------------------------------------------------

EVENT_TYPES = {
    "run_started",
    "stage_started",
    "stage_finished",
    "catalog_exposed",
    "skill_loaded",
    "model_request",
    "model_response",
    "tool_requested",
    "tool_completed",
    "file_written",
    "handoff_created",
    "limit_reached",
    "evaluation_completed",
    "run_finished",
    "run_error",
}


class Event(VersionedRecord):
    event_id: str
    run_id: str
    stage_id: str | None
    sequence: int
    agent_id: str
    phase: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
