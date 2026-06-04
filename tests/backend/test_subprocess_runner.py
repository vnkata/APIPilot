from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.backend_write_specs import simple_openapi_content


class RecordingPopenFactory:
    def __init__(self, process: "RecordingProcess") -> None:
        self.process = process
        self.commands: list[list[str]] = []
        self.cwd_values: list[str | None] = []

    def __call__(self, command: list[str], **kwargs: Any) -> "RecordingProcess":
        self.commands.append(command)
        self.cwd_values.append(kwargs.get("cwd"))
        self.process.started.set()
        return self.process


class RecordingProcess:
    def __init__(
        self,
        *,
        returncode: int = 0,
        timeout_forever: bool = False,
        wait_until_terminated: bool = False,
    ) -> None:
        self.returncode = returncode
        self.timeout_forever = timeout_forever
        self.wait_until_terminated = wait_until_terminated
        self.started = threading.Event()
        self.done = threading.Event()
        self.terminated = False
        self.killed = False

    def wait(self, timeout: float | None = None) -> int:
        if self.timeout_forever and not self.killed:
            raise subprocess.TimeoutExpired(cmd=["fake-worker"], timeout=timeout)
        if self.wait_until_terminated:
            self.done.wait(timeout=timeout)
        if self.killed:
            self.returncode = -9
        elif self.terminated:
            self.returncode = -15
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        if not self.timeout_forever:
            self.done.set()

    def kill(self) -> None:
        self.killed = True
        self.done.set()


def test_live_execution_uses_subprocess_worker_and_dry_run_stays_in_process(tmp_path):
    from api_testing.backend.domain.write_models import ExecutionMode, ExecutionStatus
    from api_testing.backend.infrastructure.execution_runner import HybridExecutionRunner

    process = RecordingProcess(returncode=0)
    popen_factory = RecordingPopenFactory(process)
    repository, spec_storage, settings, live_execution = _execution_fixture(
        tmp_path,
        mode=ExecutionMode.LIVE,
    )
    runner = HybridExecutionRunner(
        repository,
        spec_storage,
        settings,
        popen_factory=popen_factory,
    )

    runner.submit(live_execution.execution_id)
    execution = _wait_for_terminal(repository, live_execution.execution_id)
    runner.shutdown()

    assert execution.status == ExecutionStatus.COMPLETED
    assert popen_factory.commands
    assert popen_factory.commands[0][1:4] == [
        "-m",
        "api_testing.backend.execution_worker",
        "--execution-id",
    ]

    dry_repository, dry_storage, dry_settings, dry_execution = _execution_fixture(
        tmp_path / "dry",
        mode=ExecutionMode.DRY_RUN,
    )
    dry_process = RecordingProcess(returncode=0)
    dry_popen_factory = RecordingPopenFactory(dry_process)
    dry_runner = HybridExecutionRunner(
        dry_repository,
        dry_storage,
        dry_settings,
        popen_factory=dry_popen_factory,
    )

    dry_runner.submit(dry_execution.execution_id)
    dry_result = _wait_for_terminal(dry_repository, dry_execution.execution_id)
    dry_runner.shutdown()

    assert dry_result.status == ExecutionStatus.COMPLETED
    assert dry_popen_factory.commands == []
    assert (dry_settings.cache_root / str(dry_execution.run_name) / "specification.json").is_file()


def test_live_execution_cancel_terminates_process_and_records_cancelled(tmp_path):
    from api_testing.backend.domain.write_models import ExecutionMode, ExecutionStatus
    from api_testing.backend.infrastructure.execution_runner import HybridExecutionRunner

    process = RecordingProcess(returncode=0, wait_until_terminated=True)
    popen_factory = RecordingPopenFactory(process)
    repository, spec_storage, settings, execution = _execution_fixture(
        tmp_path,
        mode=ExecutionMode.LIVE,
        timeout_seconds=30,
    )
    runner = HybridExecutionRunner(
        repository,
        spec_storage,
        settings,
        popen_factory=popen_factory,
    )
    runner.submit(execution.execution_id)
    assert process.started.wait(timeout=2)

    repository.request_execution_cancel(execution.execution_id)
    runner.cancel(execution.execution_id)
    result = _wait_for_terminal(repository, execution.execution_id)
    runner.shutdown()

    assert process.terminated is True
    assert result.status == ExecutionStatus.CANCELLED
    assert repository.list_execution_events(execution.execution_id)[-1].event_type == "cancelled"


def test_live_execution_timeout_kills_process_and_records_failed(tmp_path):
    from api_testing.backend.domain.write_models import ExecutionMode, ExecutionStatus
    from api_testing.backend.infrastructure.execution_runner import HybridExecutionRunner

    process = RecordingProcess(timeout_forever=True)
    popen_factory = RecordingPopenFactory(process)
    repository, spec_storage, settings, execution = _execution_fixture(
        tmp_path,
        mode=ExecutionMode.LIVE,
        timeout_seconds=1,
    )
    runner = HybridExecutionRunner(
        repository,
        spec_storage,
        settings,
        popen_factory=popen_factory,
    )

    runner.submit(execution.execution_id)
    result = _wait_for_terminal(repository, execution.execution_id)
    runner.shutdown()

    assert process.terminated is True
    assert process.killed is True
    assert result.status == ExecutionStatus.FAILED
    assert result.summary["reason"] == "timeout"
    assert _wait_for_event(repository, execution.execution_id, "failed").metadata[
        "reason"
    ] == "timeout"


def test_publish_run_artifacts_fails_when_target_exists(tmp_path):
    from api_testing.backend.domain.errors import InvalidArtifactRequest
    from api_testing.backend.infrastructure.execution_runner import publish_run_artifacts

    source = tmp_path / "workspace" / ".cache" / "run-a"
    target = tmp_path / ".cache" / "run-a"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "specification.json").write_text("{}", encoding="utf-8")
    (target / "specification.json").write_text("old", encoding="utf-8")

    with pytest.raises(InvalidArtifactRequest, match="already exists"):
        publish_run_artifacts(source, target)

    assert (target / "specification.json").read_text(encoding="utf-8") == "old"


def test_worker_normalizes_relative_local_huggingface_embedding_path(tmp_path, monkeypatch):
    from api_testing.backend.execution_worker import _normalize_embedding_config

    model_dir = tmp_path / "models" / "embedding"
    model_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    normalized = _normalize_embedding_config(
        {
            "provider": "huggingface",
            "model": "models/embedding",
            "use_half": False,
        }
    )
    remote_id = _normalize_embedding_config(
        {
            "provider": "huggingface",
            "model": "vendor/model-name",
        }
    )

    assert normalized["model"] == str(model_dir.resolve())
    assert remote_id["model"] == "vendor/model-name"


def _execution_fixture(
    tmp_path,
    *,
    mode,
    timeout_seconds: int = 10,
):
    from api_testing.backend.domain.write_models import RunConfigCreate, SpecCreate
    from api_testing.backend.infrastructure.spec_storage import FileSpecStorage
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )
    from api_testing.backend.settings import BackendSettings

    cache_root = Path(tmp_path) / ".cache"
    spec_root = Path(tmp_path) / "specs"
    settings = BackendSettings(
        cache_root=cache_root,
        metadata_db_path=Path(tmp_path) / "backend.db",
        spec_storage_root=spec_root,
        allowed_target_base_urls=("https://example.test",),
        max_active_executions=2,
        default_execution_timeout_seconds=timeout_seconds,
        subprocess_cancel_grace_seconds=0,
    )
    repository = SQLiteWriteMetadataRepository(settings.metadata_db_path)
    spec_storage = FileSpecStorage(settings.spec_storage_root)
    stored = spec_storage.save_spec("items.json", simple_openapi_content())
    spec = repository.create_spec(
        SpecCreate(
            filename="items.json",
            title="Items API",
            content_hash=stored.content_hash,
            storage_path=stored.storage_path,
            operation_count=2,
        )
    )
    config = repository.create_run_config(
        RunConfigCreate(
            name="config",
            spec_id=spec.spec_id,
            base_url="https://example.test",
            live_api=mode.value == "live",
            request_budget=5,
            timeout_seconds=timeout_seconds,
            config={
                "spec_id": spec.spec_id,
                "base_url": "https://example.test",
                "live_api": mode.value == "live",
                "request_budget": 5,
                "timeout_seconds": timeout_seconds,
                "num_generations": 1,
                "num_test_cases": 1,
            },
        )
    )
    execution = repository.create_execution(
        spec_id=spec.spec_id,
        run_config_id=config.run_config_id,
        mode=mode,
        run_name=f"{mode.value}-run",
    )
    return repository, spec_storage, settings, execution


def _wait_for_terminal(repository, execution_id: str):
    for _ in range(100):
        execution = repository.get_execution(execution_id)
        if execution.status.value in {"completed", "failed", "cancelled"}:
            return execution
        time.sleep(0.02)
    raise AssertionError("execution did not reach terminal status")


def _wait_for_event(repository, execution_id: str, event_type: str):
    for _ in range(100):
        for event in repository.list_execution_events(execution_id):
            if event.event_type == event_type:
                return event
        time.sleep(0.02)
    raise AssertionError(f"event {event_type!r} was not recorded")
