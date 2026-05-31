from __future__ import annotations

import concurrent.futures
from pathlib import Path

from tests.backend_write_fixtures import simple_openapi_content


def test_sqlite_write_metadata_repository_persists_records_and_events(tmp_path):
    from api_testing.backend.domain.write_models import (
        ExecutionMode,
        ExecutionStatus,
        RunConfigCreate,
        SpecCreate,
    )
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )

    db_path = tmp_path / "backend.db"
    repository = SQLiteWriteMetadataRepository(db_path)

    spec = repository.create_spec(
        SpecCreate(
            filename="items.json",
            title="Items API",
            content_hash="hash-1",
            storage_path=Path("specs/items.json"),
            operation_count=2,
        )
    )
    config = repository.create_run_config(
        RunConfigCreate(
            name="dry-run config",
            spec_id=spec.spec_id,
            base_url="https://example.test",
            live_api=False,
            request_budget=5,
            timeout_seconds=10,
            config={"llm": {"api_key": {"type": "env", "name": "OPENAI_API_KEY"}}},
        )
    )
    execution = repository.create_execution(
        spec_id=spec.spec_id,
        run_config_id=config.run_config_id,
        mode=ExecutionMode.DRY_RUN,
        run_name="Items API execution",
    )
    first_event = repository.append_execution_event(
        execution.execution_id,
        event_type="queued",
        phase="execution",
        message="Execution queued",
        status=ExecutionStatus.QUEUED,
        metadata={"api_key": "secret", "safe": "visible"},
    )
    second_event = repository.append_execution_event(
        execution.execution_id,
        event_type="completed",
        phase="execution",
        message="Execution completed",
        status=ExecutionStatus.COMPLETED,
        metadata={},
    )
    repository.update_execution_status(
        execution.execution_id,
        ExecutionStatus.COMPLETED,
        summary={"generated_artifacts": 1},
    )

    reopened = SQLiteWriteMetadataRepository(db_path)

    assert reopened.get_spec(spec.spec_id).title == "Items API"
    assert reopened.get_run_config(config.run_config_id).base_url == "https://example.test"
    assert reopened.get_execution(execution.execution_id).status == ExecutionStatus.COMPLETED
    assert reopened.get_execution(execution.execution_id).summary == {
        "generated_artifacts": 1
    }
    events = reopened.list_execution_events(execution.execution_id)
    assert [event.sequence for event in events] == [
        first_event.sequence,
        second_event.sequence,
    ]
    assert reopened.list_execution_events(
        execution.execution_id,
        after_sequence=first_event.sequence,
    )[0].event_type == "completed"
    assert "secret" not in str(events[0].metadata)
    assert events[0].metadata["api_key"] == "<REDACTED>"


def test_spec_storage_saves_content_and_previews_operations(tmp_path):
    from api_testing.backend.application.openapi_specs import preview_openapi_operations
    from api_testing.backend.infrastructure.spec_storage import FileSpecStorage

    storage = FileSpecStorage(tmp_path / "specs")

    stored = storage.save_spec("items.json", simple_openapi_content())
    preview = preview_openapi_operations(storage.read_spec(stored.storage_path))

    assert stored.storage_path.name.endswith(".json")
    assert stored.content_hash
    assert preview.title == "Items API"
    assert [operation.operation_id for operation in preview.operations] == [
        "get-/items",
        "post-/items",
    ]


def test_sqlite_create_execution_with_capacity_is_atomic(tmp_path):
    from api_testing.backend.domain.errors import InvalidArtifactRequest
    from api_testing.backend.domain.write_models import (
        ExecutionMode,
        RunConfigCreate,
        SpecCreate,
    )
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )

    repository = SQLiteWriteMetadataRepository(tmp_path / "backend.db")
    spec = repository.create_spec(
        SpecCreate(
            filename="items.json",
            title="Items API",
            content_hash="hash-1",
            storage_path=Path("specs/items.json"),
            operation_count=2,
        )
    )
    config = repository.create_run_config(
        RunConfigCreate(
            name="live config",
            spec_id=spec.spec_id,
            base_url="https://example.test",
            live_api=True,
            request_budget=5,
            timeout_seconds=10,
            config={},
        )
    )

    def create(index: int):
        try:
            return repository.create_execution_with_capacity(
                spec_id=spec.spec_id,
                run_config_id=config.run_config_id,
                mode=ExecutionMode.LIVE,
                run_name=f"live-{index}",
                max_active_executions=2,
            ).execution_id
        except InvalidArtifactRequest:
            return "rejected"

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(create, range(4)))

    assert sum(result != "rejected" for result in results) == 2
    assert sum(result == "rejected" for result in results) == 2
    assert repository.count_active_executions() == 2
    assert [
        event.event_type
        for execution in repository.list_executions()
        for event in repository.list_execution_events(execution.execution_id)
    ] == ["queued", "queued"]


def test_sqlite_reconciles_orphaned_active_executions(tmp_path):
    from api_testing.backend.domain.write_models import (
        ExecutionMode,
        ExecutionStatus,
        RunConfigCreate,
        SpecCreate,
    )
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )

    repository = SQLiteWriteMetadataRepository(tmp_path / "backend.db")
    spec = repository.create_spec(
        SpecCreate(
            filename="items.json",
            title="Items API",
            content_hash="hash-1",
            storage_path=Path("specs/items.json"),
            operation_count=2,
        )
    )
    config = repository.create_run_config(
        RunConfigCreate(
            name="live config",
            spec_id=spec.spec_id,
            base_url="https://example.test",
            live_api=True,
            request_budget=5,
            timeout_seconds=10,
            config={},
        )
    )
    execution = repository.create_execution(
        spec_id=spec.spec_id,
        run_config_id=config.run_config_id,
        mode=ExecutionMode.LIVE,
        run_name="orphaned-live",
    )
    repository.mark_execution_running(execution.execution_id)

    reconciled = repository.reconcile_orphaned_executions(reason="worker_orphaned")

    assert [item.execution_id for item in reconciled] == [execution.execution_id]
    assert (
        repository.get_execution(execution.execution_id).status
        == ExecutionStatus.FAILED
    )
    events = repository.list_execution_events(execution.execution_id)
    assert events[-1].event_type == "worker_orphaned"
    assert events[-1].metadata["reason"] == "worker_orphaned"


def test_sqlite_event_sequences_remain_ordered_under_concurrent_appends(tmp_path):
    from api_testing.backend.domain.write_models import (
        ExecutionMode,
        RunConfigCreate,
        SpecCreate,
    )
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )

    repository = SQLiteWriteMetadataRepository(tmp_path / "backend.db")
    spec = repository.create_spec(
        SpecCreate(
            filename="items.json",
            title="Items API",
            content_hash="hash-1",
            storage_path=Path("specs/items.json"),
            operation_count=2,
        )
    )
    config = repository.create_run_config(
        RunConfigCreate(
            name="dry config",
            spec_id=spec.spec_id,
            base_url="https://example.test",
            live_api=False,
            request_budget=5,
            timeout_seconds=10,
            config={},
        )
    )
    execution = repository.create_execution(
        spec_id=spec.spec_id,
        run_config_id=config.run_config_id,
        mode=ExecutionMode.DRY_RUN,
        run_name="events",
    )

    def append(index: int) -> int:
        return repository.append_execution_event(
            execution.execution_id,
            event_type=f"event_{index}",
            metadata={"index": index},
        ).sequence

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        sequences = list(pool.map(append, range(20)))

    events = repository.list_execution_events(execution.execution_id)
    assert sorted(sequences) == list(range(1, 21))
    assert [event.sequence for event in events] == list(range(1, 21))


def test_sqlite_wal_and_indexes_are_initialized(tmp_path):
    import sqlite3

    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )

    repository = SQLiteWriteMetadataRepository(tmp_path / "backend.db")

    with sqlite3.connect(repository.db_path) as connection:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        index_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()

    assert journal_mode.lower() == "wal"
    assert {
        "idx_run_configs_spec_id",
        "idx_executions_status_created_at",
        "idx_execution_events_execution_sequence",
    }.issubset({row[0] for row in index_rows})
