from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.fixtures.backend_artifacts import (
    add_combination_artifacts,
    build_artifact_cache,
    write_json,
)


def _client(cache_root: Path) -> TestClient:
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    return TestClient(create_app(BackendSettings(cache_root=cache_root)))


def _cache_with_combination(tmp_path: Path) -> Path:
    cache_root = build_artifact_cache(tmp_path)
    return add_combination_artifacts(cache_root)


def test_catalog_exposes_new_combination_and_contextual_memory_artifacts(tmp_path):
    client = _client(_cache_with_combination(tmp_path))

    response = client.get("/api/v1/runs/Run%20A/artifacts")

    assert response.status_code == 200
    artifacts = {
        artifact["artifact_id"]: artifact for artifact in response.json()["artifacts"]
    }
    assert artifacts["combine_constraint_miners"]["kind"] == "combined_constraints"
    assert artifacts["combine_constraint_miners"]["media_type"] == "application/json"
    assert artifacts["combine_constraint_miners"]["raw_policy"] == "raw_json"
    assert artifacts["combine_constraint_miners"]["raw_supported"] is True
    assert artifacts["contextual_memory_db"]["kind"] == "memory"
    assert artifacts["contextual_memory_db"]["media_type"] == "application/octet-stream"
    assert artifacts["contextual_memory_db"]["raw_policy"] == "summary_only"
    assert artifacts["contextual_memory_db"]["raw_supported"] is False


def test_artifact_content_supports_raw_combine_and_summary_only_memory_db(tmp_path):
    client = _client(_cache_with_combination(tmp_path))

    raw_response = client.get(
        "/api/v1/runs/Run%20A/artifacts/combine_constraint_miners/content",
        params={"raw": "true"},
    )
    memory_summary_response = client.get(
        "/api/v1/runs/Run%20A/artifacts/contextual_memory_db/content"
    )
    memory_raw_response = client.get(
        "/api/v1/runs/Run%20A/artifacts/contextual_memory_db/content",
        params={"raw": "true"},
    )

    assert raw_response.status_code == 200
    raw_payload = raw_response.json()
    assert raw_payload["content"]["content_kind"] == "raw_json"
    assert raw_payload["content"]["value"]["get-/items"]["return.items[].id"][
        "status"
    ] == "RESOLVED"
    assert raw_payload["content"]["value"]["get-/items"]["return.items[].id"][
        "relation"
    ] == "EQUIVALENT"

    assert memory_summary_response.status_code == 200
    memory_summary = memory_summary_response.json()["content"]
    assert memory_summary["content_kind"] == "summary"
    assert memory_summary["context_count"] == 2
    context = memory_summary["contexts"][0]
    assert {
        key: context[key]
        for key in (
            "context_key",
            "context_kind",
            "payload_kind",
            "item_count",
            "whitelist_count",
            "blacklist_count",
        )
    } == {
        "context_key": "get-/items",
        "context_kind": "operation",
        "payload_kind": "object",
        "item_count": 0,
        "whitelist_count": 1,
        "blacklist_count": 1,
    }
    assert context["updated_at"]

    assert memory_raw_response.status_code == 400
    assert memory_raw_response.json()["error"]["code"] == "invalid_request"


def test_combination_entries_summary_facets_and_detail_are_typed_and_sanitized(tmp_path):
    client = _client(_cache_with_combination(tmp_path))

    summary_response = client.get("/api/v1/runs/Run%20A/constraints/combination/summary")
    entries_response = client.get(
        "/api/v1/runs/Run%20A/constraints/combination/entries",
        params={
            "operation_id": "get-/items",
            "relation": "EQUIVALENT",
            "resolved": "true",
            "group_by": "status",
            "sort_by": "property_path",
        },
    )

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["source_artifact"] == "combine_constraint_miners"
    assert summary["endpoint_count"] == 1
    assert summary["property_count"] == 2
    assert summary["resolved_count"] == 1
    assert summary["unresolved_count"] == 1
    assert summary["malformed_count"] == 1
    assert summary["status_counts"]["RESOLVED"] == 1
    assert summary["status_counts"]["CONFLICT"] == 1
    assert summary["relation_counts"]["EQUIVALENT"] == 1
    assert summary["relation_counts"]["DISJOINT"] == 1
    assert summary["runtime_verdict_counts"]["BOTH_TRUE"] == 1

    assert entries_response.status_code == 200
    entries = entries_response.json()
    assert entries["pagination"]["total"] == 1
    assert entries["groups"] == [{"key": "RESOLVED", "count": 1}]
    entry = entries["items"][0]
    assert entry["operation_id"] == "get-/items"
    assert entry["property_path"] == "return.items[].id"
    assert entry["status"] == "RESOLVED"
    assert entry["relation"] == "EQUIVALENT"
    assert entry["runtime_verdict"] == "BOTH_TRUE"
    assert entry["resolved"] is True
    assert entry["validation_case_count"] == 1
    assert entry["has_counter_example"] is True
    assert entry["has_runtime_evaluation"] is True

    facets_response = client.get(
        "/api/v1/runs/Run%20A/constraints/combination/facets",
        params={"operation_id": "get-/items"},
    )
    assert facets_response.status_code == 200
    facets = facets_response.json()
    assert {"key": "RESOLVED", "count": 1} in facets["status"]
    assert {"key": "EQUIVALENT", "count": 1} in facets["relation"]
    assert {"key": "BOTH_TRUE", "count": 1} in facets["runtime_verdict"]
    assert {"key": "true", "count": 1} in facets["resolved"]

    detail_response = client.get(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{entry['combination_id']}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    encoded_detail = json.dumps(detail)
    assert detail["reason"] == "Resolved by equivalent static and dynamic evidence."
    assert detail["counter_example"]["staged_payload"]["headers"]["Authorization"] == (
        "<REDACTED>"
    )
    assert detail["validation_cases"][0]["response_payload"]["token"] == "<REDACTED>"
    assert detail["raw_record_sanitized"]["counter_example"]["staged_payload"][
        "body"
    ]["api_key"] == "<REDACTED>"
    assert "combo-secret" not in encoded_detail
    assert "case-password" not in encoded_detail
    assert "case-response-token" not in encoded_detail


def test_combination_parser_skips_malformed_records_but_fails_when_none_valid(tmp_path):
    cache_root = build_artifact_cache(tmp_path)
    run_dir = cache_root / "Run A"
    write_json(
        run_dir / "combine_constraint_miners.json",
        {
            "get-/items": {
                "bad": "not a dict",
                "good": {
                    "status": "UNIQUE_STATIC",
                    "relation": None,
                    "final_constraint": "required",
                },
            }
        },
    )
    client = _client(cache_root)

    response = client.get("/api/v1/runs/Run%20A/constraints/combination/entries")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["malformed_count"] == 1
    assert payload["warnings"]

    write_json(run_dir / "combine_constraint_miners.json", {"get-/items": {"bad": []}})
    response = client.get("/api/v1/runs/Run%20A/constraints/combination/entries")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert "regenerate required" in response.json()["error"]["message"]


def test_combination_parser_rejects_old_format_paired_records(tmp_path):
    cache_root = build_artifact_cache(tmp_path)
    run_dir = cache_root / "Run A"
    write_json(
        run_dir / "combine_constraint_miners.json",
        {
            "get-/items": {
                "return.items[].id": {
                    "endpoint": "get-/items",
                    "property": "return.items[].id",
                    "static_constraint": "return.items.id >= 1",
                    "dynamic_constraint": "return.items.id >= 1",
                    "status": "COMBINED_EQUIVALENT",
                    "final_constraint": "return.items.id >= 1",
                    "reason": "Old binary format.",
                }
            }
        },
    )
    client = _client(cache_root)

    response = client.get("/api/v1/runs/Run%20A/constraints/combination/entries")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_constraint_explorer_prefers_resolved_new_combination_artifact(tmp_path):
    client = _client(_cache_with_combination(tmp_path))

    response = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={
            "source": "combined",
            "operation_id": "get-/items",
            "sort_by": "property_path",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["combined_source"] == "combine_constraint_miners"
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["property_path"] == "return.items[].id"
    assert payload["items"][0]["expression"] == (
        "return.items.id >= 1 and return.items.id <= 100"
    )
    assert payload["items"][0]["combined_expression"] == (
        "return.items.id >= 1 and return.items.id <= 100"
    )
