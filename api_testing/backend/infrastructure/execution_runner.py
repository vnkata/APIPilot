"""Execution runners for backend write-flow orchestration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Protocol

from api_testing.backend.application.openapi_specs import preview_openapi_operations
from api_testing.backend.application.write_ports import (
    SpecStorageProtocol,
    WriteMetadataRepositoryProtocol,
)
from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.write_models import (
    ExecutionMode,
    ExecutionStatus,
)
from api_testing.backend.settings import BackendSettings


class ProcessProtocol(Protocol):
    returncode: int | None

    def wait(self, timeout: float | None = None) -> int: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...


PopenFactory = Callable[..., ProcessProtocol]


class HybridExecutionRunner:
    """Runs dry executions in-process and live executions in subprocesses."""

    def __init__(
        self,
        repository: WriteMetadataRepositoryProtocol,
        spec_storage: SpecStorageProtocol,
        settings: BackendSettings,
        *,
        popen_factory: PopenFactory | None = None,
    ) -> None:
        self.repository = repository
        self.spec_storage = spec_storage
        self.settings = settings
        self._popen_factory = popen_factory or subprocess.Popen
        self._executor = ThreadPoolExecutor(max_workers=settings.max_active_executions)
        self._processes: dict[str, ProcessProtocol] = {}
        self._process_lock = threading.Lock()

    def submit(self, execution_id: str) -> None:
        self._executor.submit(self._run, execution_id)

    def cancel(self, execution_id: str) -> None:
        process = self._process_for(execution_id)
        if process is None:
            return
        self._terminate_process(process)
        self._finalize_if_active(
            execution_id,
            ExecutionStatus.CANCELLED,
            event_type="cancelled",
            message="Execution cancelled",
            summary={"reason": "cancelled"},
        )

    def shutdown(self) -> None:
        with self._process_lock:
            processes = list(self._processes.values())
            self._processes.clear()
        for process in processes:
            self._terminate_process(process)
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, execution_id: str) -> None:
        try:
            execution = self.repository.get_execution(execution_id)
            if self.repository.is_cancel_requested(execution_id):
                self._finalize_if_active(
                    execution_id,
                    ExecutionStatus.CANCELLED,
                    event_type="cancelled",
                    message="Execution cancelled",
                    summary={"reason": "cancelled"},
                )
                return
            if execution.mode == ExecutionMode.LIVE:
                self._run_live(execution_id)
            else:
                self._run_dry(execution_id)
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            self._finalize_if_active(
                execution_id,
                ExecutionStatus.FAILED,
                event_type="failed",
                message="Execution failed",
                summary={
                    "reason": "runner_error",
                    "error_type": type(exc).__name__,
                },
            )

    def _run_dry(self, execution_id: str) -> None:
        execution = self.repository.mark_execution_running(execution_id)
        self.repository.append_execution_event(
            execution_id,
            event_type="running",
            phase="execution",
            message="Execution started",
            status=ExecutionStatus.RUNNING,
        )
        spec = self.repository.get_spec(execution.spec_id)
        content = self.spec_storage.read_spec(spec.storage_path)
        preview = preview_openapi_operations(content)
        run_dir = self.settings.cache_root / str(execution.run_name)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "baseline_specification.json").write_text(content, encoding="utf-8")
        (run_dir / "specification.json").write_text(
            json.dumps(
                preview.normalized_specification,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        if self.repository.is_cancel_requested(execution_id):
            self._finalize_if_active(
                execution_id,
                ExecutionStatus.CANCELLED,
                event_type="cancelled",
                message="Execution cancelled",
                summary={"reason": "cancelled"},
            )
            return
        self._finalize_if_active(
            execution_id,
            ExecutionStatus.COMPLETED,
            event_type="completed",
            message="Execution completed",
            summary={
                "mode": "dry_run",
                "operation_count": len(preview.operations),
                "generated_artifacts": 2,
            },
        )

    def _run_live(self, execution_id: str) -> None:
        execution = self.repository.mark_execution_running(execution_id)
        self.repository.append_execution_event(
            execution_id,
            event_type="running",
            phase="execution",
            message="Execution started",
            status=ExecutionStatus.RUNNING,
        )
        command = self._worker_command(execution_id)
        process = self._popen_factory(command)
        with self._process_lock:
            self._processes[execution_id] = process
        try:
            timeout_seconds = self._execution_timeout_seconds(execution.run_config_id)
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self._terminate_process(process)
            self._finalize_if_active(
                execution_id,
                ExecutionStatus.FAILED,
                event_type="failed",
                message="Execution timed out",
                summary={"reason": "timeout"},
            )
            return
        finally:
            with self._process_lock:
                self._processes.pop(execution_id, None)

        if self.repository.is_cancel_requested(execution_id):
            self._finalize_if_active(
                execution_id,
                ExecutionStatus.CANCELLED,
                event_type="cancelled",
                message="Execution cancelled",
                summary={"reason": "cancelled"},
            )
        elif returncode == 0:
            self._finalize_if_active(
                execution_id,
                ExecutionStatus.COMPLETED,
                event_type="completed",
                message="Execution completed",
                summary={"mode": "live", "worker_exit_code": returncode},
            )
        else:
            self._finalize_if_active(
                execution_id,
                ExecutionStatus.FAILED,
                event_type="failed",
                message="Execution worker failed",
                summary={"reason": "worker_exit", "worker_exit_code": returncode},
            )

    def _worker_command(self, execution_id: str) -> list[str]:
        command = [
            sys.executable,
            "-m",
            "api_testing.backend.execution_worker",
            "--execution-id",
            execution_id,
            "--metadata-db-path",
            str(self.settings.metadata_db_path),
            "--cache-root",
            str(self.settings.cache_root),
            "--spec-storage-root",
            str(self.settings.spec_storage_root),
            "--default-async-max-concurrent",
            str(self.settings.default_async_max_concurrent),
        ]
        for target in self.settings.allowed_target_base_urls:
            command.extend(["--allowed-target-base-url", target])
        return command

    def _execution_timeout_seconds(self, run_config_id: str) -> int:
        config = self.repository.get_run_config(run_config_id)
        return int(config.timeout_seconds or self.settings.default_execution_timeout_seconds)

    def _process_for(self, execution_id: str) -> ProcessProtocol | None:
        with self._process_lock:
            return self._processes.get(execution_id)

    def _terminate_process(self, process: ProcessProtocol) -> None:
        try:
            process.terminate()
            process.wait(timeout=self.settings.subprocess_cancel_grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass

    def _finalize_if_active(
        self,
        execution_id: str,
        status: ExecutionStatus,
        *,
        event_type: str,
        message: str,
        summary: dict[str, Any],
    ) -> None:
        self.repository.finalize_active_execution_with_event(
            execution_id,
            status,
            event_type=event_type,
            phase="execution",
            message=message,
            summary=summary,
        )


InProcessExecutionRunner = HybridExecutionRunner


def publish_run_artifacts(source_run_dir: Path, target_run_dir: Path) -> None:
    """Atomically publish a completed run directory into the configured cache root."""
    source_run_dir = Path(source_run_dir)
    target_run_dir = Path(target_run_dir)
    if not source_run_dir.is_dir():
        raise InvalidArtifactRequest(f"Run artifact directory not found: {source_run_dir}")
    if target_run_dir.exists():
        raise InvalidArtifactRequest(f"Run artifact directory already exists: {target_run_dir}")
    target_run_dir.parent.mkdir(parents=True, exist_ok=True)
    source_run_dir.rename(target_run_dir)


def _resolve_secret_refs(value: Any) -> Any:
    if isinstance(value, dict) and value.get("type") == "env" and "name" in value:
        return os.getenv(str(value["name"]), "")
    if isinstance(value, dict):
        return {str(key): _resolve_secret_refs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_secret_refs(item) for item in value]
    return value


def _build_llm_config(llm: dict[str, Any]) -> dict[str, Any]:
    provider = str(llm.get("provider") or "openai")
    model = str(llm.get("model") or "gpt-4.1-mini")
    base = {
        "provider": provider,
        "model": model,
        "temperature": float(llm.get("temperature") or 0.0),
        provider: {},
    }
    provider_config = dict(llm)
    provider_config.pop("provider", None)
    provider_config.pop("model", None)
    provider_config.pop("temperature", None)
    base[provider] = provider_config
    return base


def _build_embedding_config(embedding: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": embedding.get("provider") or "huggingface",
        "model": embedding.get("model") or "google/embeddinggemma-300m",
        "use_half": bool(embedding.get("use_half", False)),
        "ollama": {"base_url": embedding.get("base_url") or "http://localhost:11434"},
    }
