"""Domain models for APIPilot backend write-flow orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


JsonMap = dict[str, Any]


class ExecutionMode(StrEnum):
    DRY_RUN = "dry_run"
    LIVE = "live"


class ExecutionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_EXECUTION_STATUSES = {
    ExecutionStatus.CANCELLED,
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
}


ACTIVE_EXECUTION_STATUSES = {
    ExecutionStatus.QUEUED,
    ExecutionStatus.RUNNING,
    ExecutionStatus.CANCEL_REQUESTED,
}


@dataclass(frozen=True, slots=True)
class SpecCreate:
    filename: str
    title: str
    content_hash: str
    storage_path: Path
    operation_count: int


@dataclass(frozen=True, slots=True)
class UploadedSpec:
    spec_id: str
    filename: str
    title: str
    content_hash: str
    storage_path: Path
    operation_count: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredSpec:
    filename: str
    content_hash: str
    storage_path: Path


@dataclass(frozen=True, slots=True)
class OpenAPIOperation:
    operation_id: str
    display_operation_id: str | None
    method: str
    path: str
    summary: str | None
    has_request_body: bool
    response_statuses: list[str]


@dataclass(frozen=True, slots=True)
class OpenAPIPreview:
    title: str
    version: str | None
    operations: list[OpenAPIOperation]
    normalized_specification: JsonMap


@dataclass(frozen=True, slots=True)
class RunConfigCreate:
    name: str
    spec_id: str
    base_url: str
    live_api: bool
    request_budget: int | None
    timeout_seconds: int | None
    config: JsonMap


@dataclass(frozen=True, slots=True)
class RunConfig:
    run_config_id: str
    name: str
    spec_id: str
    base_url: str
    live_api: bool
    request_budget: int | None
    timeout_seconds: int | None
    config: JsonMap
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RunConfigValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Execution:
    execution_id: str
    spec_id: str
    run_config_id: str
    mode: ExecutionMode
    status: ExecutionStatus
    run_name: str | None
    summary: JsonMap
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    event_id: str
    execution_id: str
    sequence: int
    event_type: str
    phase: str | None
    message: str | None
    status: ExecutionStatus | None
    metadata: JsonMap
    created_at: datetime

