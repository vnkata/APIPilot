"""Application ports for APIPilot write-flow orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from api_testing.backend.domain.write_models import (
    Execution,
    ExecutionEvent,
    ExecutionMode,
    ExecutionStatus,
    RunConfig,
    RunConfigCreate,
    SpecCreate,
    StoredSpec,
    UploadedSpec,
)


class SpecStorageProtocol(Protocol):
    def save_spec(
        self,
        filename: str,
        content: str,
        *,
        spec_id: str | None = None,
    ) -> StoredSpec: ...

    def read_spec(self, storage_path: Path) -> str: ...


class WriteMetadataRepositoryProtocol(Protocol):
    def create_spec(
        self,
        spec: SpecCreate,
        *,
        spec_id: str | None = None,
    ) -> UploadedSpec: ...

    def list_specs(self) -> list[UploadedSpec]: ...

    def get_spec(self, spec_id: str) -> UploadedSpec: ...

    def create_run_config(
        self,
        config: RunConfigCreate,
        *,
        run_config_id: str | None = None,
    ) -> RunConfig: ...

    def list_run_configs(self) -> list[RunConfig]: ...

    def get_run_config(self, run_config_id: str) -> RunConfig: ...

    def create_execution(
        self,
        *,
        spec_id: str,
        run_config_id: str,
        mode: ExecutionMode,
        run_name: str,
        execution_id: str | None = None,
    ) -> Execution: ...

    def list_executions(self) -> list[Execution]: ...

    def get_execution(self, execution_id: str) -> Execution: ...

    def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        *,
        summary: dict | None = None,
        error_message: str | None = None,
    ) -> Execution: ...

    def mark_execution_running(self, execution_id: str) -> Execution: ...

    def request_execution_cancel(self, execution_id: str) -> Execution: ...

    def count_active_executions(self) -> int: ...

    def is_cancel_requested(self, execution_id: str) -> bool: ...

    def append_execution_event(
        self,
        execution_id: str,
        *,
        event_type: str,
        phase: str | None = None,
        message: str | None = None,
        status: ExecutionStatus | None = None,
        metadata: dict | None = None,
    ) -> ExecutionEvent: ...

    def list_execution_events(
        self,
        execution_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[ExecutionEvent]: ...


class ExecutionRunnerProtocol(Protocol):
    def submit(self, execution_id: str) -> None: ...

