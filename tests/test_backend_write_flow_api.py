from __future__ import annotations

import time

from fastapi.testclient import TestClient

from tests.backend_write_fixtures import simple_openapi_content


def _client(tmp_path, *, allowed_targets=("https://example.test",), max_active=2):
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    settings = BackendSettings(
        cache_root=tmp_path / ".cache",
        metadata_db_path=tmp_path / "backend.db",
        spec_storage_root=tmp_path / "specs",
        allowed_target_base_urls=allowed_targets,
        max_active_executions=max_active,
        default_request_budget=5,
        default_execution_timeout_seconds=10,
    )
    return TestClient(create_app(settings))


def _create_spec(client: TestClient) -> str:
    response = client.post(
        "/api/v1/specs",
        json={
            "filename": "items.json",
            "title": "Items API",
            "content": simple_openapi_content(),
        },
    )
    assert response.status_code == 201
    return response.json()["spec_id"]


def _run_config_payload(spec_id: str, *, live_api: bool = False):
    return {
        "name": "items config",
        "spec_id": spec_id,
        "base_url": "https://example.test",
        "live_api": live_api,
        "request_budget": 5,
        "timeout_seconds": 10,
        "num_generations": 1,
        "num_test_cases": 2,
        "constraint_mining": False,
        "llm": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "api_key": {"type": "env", "name": "OPENAI_API_KEY"},
        },
        "embedding": {"provider": "huggingface", "model": "test-embedding"},
        "headers": {"Authorization": {"type": "env", "name": "API_TOKEN"}},
    }


def _create_run_config(client: TestClient, spec_id: str, *, live_api: bool = False) -> str:
    response = client.post(
        "/api/v1/run-configs",
        json=_run_config_payload(spec_id, live_api=live_api),
    )
    assert response.status_code == 201
    return response.json()["run_config_id"]


def test_specs_api_uploads_lists_and_previews_operations(tmp_path):
    client = _client(tmp_path)

    spec_id = _create_spec(client)

    list_response = client.get("/api/v1/specs")
    detail_response = client.get(f"/api/v1/specs/{spec_id}")
    operations_response = client.get(f"/api/v1/specs/{spec_id}/operations")

    assert list_response.status_code == 200
    assert [spec["spec_id"] for spec in list_response.json()["specs"]] == [spec_id]
    assert detail_response.status_code == 200
    assert detail_response.json()["content"] is None
    assert detail_response.json()["operation_count"] == 2
    assert operations_response.status_code == 200
    operations = operations_response.json()["operations"]
    assert [operation["operation_id"] for operation in operations] == [
        "get-/items",
        "post-/items",
    ]
    assert operations[1]["has_request_body"] is True


def test_run_config_api_validates_persists_and_redacts_secret_refs(tmp_path):
    client = _client(tmp_path)
    spec_id = _create_spec(client)
    payload = _run_config_payload(spec_id)

    validate_response = client.post("/api/v1/run-configs/validate", json=payload)
    create_response = client.post("/api/v1/run-configs", json=payload)

    assert validate_response.status_code == 200
    assert validate_response.json() == {"valid": True, "errors": []}
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["spec_id"] == spec_id
    assert body["llm"]["api_key"] == {"type": "env", "configured": True}
    assert body["headers"]["Authorization"] == {"type": "env", "configured": True}
    assert "OPENAI_API_KEY" not in str(body)
    assert "API_TOKEN" not in str(body)


def test_executions_api_runs_dry_run_and_maps_to_existing_run_reader(tmp_path):
    client = _client(tmp_path)
    spec_id = _create_spec(client)
    run_config_id = _create_run_config(client, spec_id)

    create_response = client.post(
        "/api/v1/executions",
        json={
            "spec_id": spec_id,
            "run_config_id": run_config_id,
            "mode": "dry_run",
        },
    )

    assert create_response.status_code == 202
    execution_id = create_response.json()["execution_id"]
    execution = _wait_for_terminal_execution(client, execution_id)
    assert execution["status"] == "completed"
    assert execution["run_name"]

    events_response = client.get(
        f"/api/v1/executions/{execution_id}/events",
        params={"after_sequence": 0},
    )
    run_response = client.get(f"/api/v1/executions/{execution_id}/run")
    summary_response = client.get(
        f"/api/v1/runs/{execution['run_name']}/summary",
    )

    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()["events"]] == [
        "queued",
        "running",
        "completed",
    ]
    assert run_response.status_code == 200
    assert run_response.json()["run_name"] == execution["run_name"]
    assert summary_response.status_code == 200
    assert summary_response.json()["operation_count"] == 2


def test_live_execution_requires_allowlist_and_budget(tmp_path):
    client = _client(tmp_path, allowed_targets=())
    spec_id = _create_spec(client)
    run_config_id = _create_run_config(client, spec_id)

    response = client.post(
        "/api/v1/executions",
        json={
            "spec_id": spec_id,
            "run_config_id": run_config_id,
            "mode": "live",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert "allowlist" in response.json()["error"]["message"]


def test_execution_active_limit_is_enforced(tmp_path):
    from api_testing.backend.domain.write_models import ExecutionMode
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )

    client = _client(tmp_path, max_active=2)
    spec_id = _create_spec(client)
    run_config_id = _create_run_config(client, spec_id)
    repository = SQLiteWriteMetadataRepository(tmp_path / "backend.db")
    repository.create_execution(
        spec_id=spec_id,
        run_config_id=run_config_id,
        mode=ExecutionMode.LIVE,
        run_name="active-1",
    )
    repository.mark_execution_running(repository.list_executions()[0].execution_id)
    repository.create_execution(
        spec_id=spec_id,
        run_config_id=run_config_id,
        mode=ExecutionMode.LIVE,
        run_name="active-2",
    )
    repository.mark_execution_running(repository.list_executions()[1].execution_id)

    response = client.post(
        "/api/v1/executions",
        json={
            "spec_id": spec_id,
            "run_config_id": run_config_id,
            "mode": "dry_run",
        },
    )

    assert response.status_code == 400
    assert "active execution limit" in response.json()["error"]["message"]


def test_execution_cancel_sets_cancel_requested_status(tmp_path):
    client = _client(tmp_path)
    spec_id = _create_spec(client)
    run_config_id = _create_run_config(client, spec_id)

    create_response = client.post(
        "/api/v1/executions",
        json={
            "spec_id": spec_id,
            "run_config_id": run_config_id,
            "mode": "dry_run",
        },
    )
    execution_id = create_response.json()["execution_id"]

    cancel_response = client.post(f"/api/v1/executions/{execution_id}/cancel")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] in {
        "cancel_requested",
        "cancelled",
        "completed",
    }


def test_create_app_reconciles_orphaned_active_executions(tmp_path):
    from api_testing.backend.app import create_app
    from api_testing.backend.domain.write_models import (
        ExecutionMode,
        ExecutionStatus,
        RunConfigCreate,
        SpecCreate,
    )
    from api_testing.backend.infrastructure.write_metadata import (
        SQLiteWriteMetadataRepository,
    )
    from api_testing.backend.settings import BackendSettings

    settings = BackendSettings(
        cache_root=tmp_path / ".cache",
        metadata_db_path=tmp_path / "backend.db",
        spec_storage_root=tmp_path / "specs",
        allowed_target_base_urls=("https://example.test",),
    )
    repository = SQLiteWriteMetadataRepository(settings.metadata_db_path)
    spec = repository.create_spec(
        SpecCreate(
            filename="items.json",
            title="Items API",
            content_hash="hash-1",
            storage_path=tmp_path / "specs" / "items.json",
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

    client = TestClient(create_app(settings))
    execution_response = client.get(f"/api/v1/executions/{execution.execution_id}")
    events_response = client.get(f"/api/v1/executions/{execution.execution_id}/events")

    assert execution_response.status_code == 200
    assert execution_response.json()["status"] == ExecutionStatus.FAILED.value
    assert execution_response.json()["summary"]["reason"] == "worker_orphaned"
    assert events_response.status_code == 200
    assert events_response.json()["events"][-1]["event_type"] == "worker_orphaned"


def _wait_for_terminal_execution(client: TestClient, execution_id: str) -> dict:
    for _ in range(50):
        response = client.get(f"/api/v1/executions/{execution_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return payload
        time.sleep(0.02)
    raise AssertionError("Execution did not reach a terminal status")
