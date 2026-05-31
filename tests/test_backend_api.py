from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.backend_artifact_fixtures import build_artifact_cache
from tests.backend_explorer_fixtures import build_explorer_artifact_cache


def _client(tmp_path) -> TestClient:
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    settings = BackendSettings(cache_root=build_artifact_cache(tmp_path))
    return TestClient(create_app(settings))


def _explorer_client(tmp_path) -> TestClient:
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    settings = BackendSettings(cache_root=build_explorer_artifact_cache(tmp_path))
    return TestClient(create_app(settings))


def test_health_endpoint(tmp_path):
    client = _client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runs_and_summary_endpoints(tmp_path):
    client = _client(tmp_path)

    runs_response = client.get("/api/v1/runs")
    summary_response = client.get("/api/v1/runs/Run%20A/summary")

    assert runs_response.status_code == 200
    assert [run["run_name"] for run in runs_response.json()["runs"]] == [
        "Canada Holidays Medium",
        "Run A",
    ]
    assert summary_response.status_code == 200
    assert summary_response.json()["operation_count"] == 2


def test_medium_canada_holidays_fixture_exercises_querying_and_redaction(tmp_path):
    client = _client(tmp_path)

    summary_response = client.get("/api/v1/runs/Canada%20Holidays%20Medium/summary")
    reports_response = client.get(
        "/api/v1/runs/Canada%20Holidays%20Medium/reports/entries",
        params={
            "group_by": "status_code",
            "limit": 2,
            "offset": 2,
            "sort_by": "operation_id",
        },
    )
    test_cases_response = client.get(
        "/api/v1/runs/Canada%20Holidays%20Medium/test-cases",
        params={
            "include_body": "true",
            "limit": 1,
            "operation_id": "get-/api/v1/holidays",
            "offset": 5,
            "status_code": 200,
        },
    )
    har_response = client.get(
        "/api/v1/runs/Canada%20Holidays%20Medium/history/sessions/session-medium/entries",
        params={"include_body": "true", "limit": 1},
    )

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["operation_count"] == 4
    assert summary["test_case_count"] >= 36
    assert summary["har_session_count"] == 2
    assert summary["report_status_counts"]["200"] == 31
    assert summary["report_status_counts"]["404"] == 3

    assert reports_response.status_code == 200
    reports_payload = reports_response.json()
    assert reports_payload["pagination"]["total"] >= 8
    assert {"key": "200", "count": 4} in reports_payload["groups"]
    assert {"key": "404", "count": 2} in reports_payload["groups"]

    assert test_cases_response.status_code == 200
    test_case = test_cases_response.json()["items"][0]
    assert test_case["response_body"]["access_token"] == "<REDACTED>"

    assert har_response.status_code == 200
    har_entry = har_response.json()["items"][0]
    assert har_entry["request_headers"]["authorization"] == "<REDACTED>"
    assert har_entry["response_body"]["access_token"] == "<REDACTED>"


def test_core_artifact_endpoints(tmp_path):
    client = _client(tmp_path)

    assert client.get("/api/v1/runs/Run%20A/artifacts").status_code == 200
    assert client.get("/api/v1/runs/Run%20A/operations").status_code == 200
    assert (
        client.get(
            "/api/v1/runs/Run%20A/operation",
            params={"operation_id": "get-/items"},
        ).json()["operation_id"]
        == "get-/items"
    )
    assert client.get("/api/v1/runs/Run%20A/reports").status_code == 200
    assert client.get("/api/v1/runs/Run%20A/graph").status_code == 200
    assert client.get("/api/v1/runs/Run%20A/constraints/static").status_code == 200
    assert client.get("/api/v1/runs/Run%20A/constraints/dynamic").status_code == 200


def test_detailed_constraint_endpoints_support_querying(tmp_path):
    client = _client(tmp_path)

    static_response = client.get(
        "/api/v1/runs/Run%20A/constraints/static/entries",
        params={
            "section": "request_response",
            "q": "input.limit",
            "group_by": "section",
        },
    )
    dynamic_response = client.get(
        "/api/v1/runs/Run%20A/constraints/dynamic/entries",
        params={"operation_id": "get-/items", "group_by": "operation_id"},
    )

    assert static_response.status_code == 200
    static_payload = static_response.json()
    assert static_payload["pagination"]["total"] == 1
    assert static_payload["items"][0]["section"] == "request_response"
    assert static_payload["items"][0]["property_path"] == "input.limit"
    assert static_payload["groups"] == [{"key": "request_response", "count": 1}]

    assert dynamic_response.status_code == 200
    dynamic_payload = dynamic_response.json()
    assert dynamic_payload["pagination"]["total"] == 1
    assert dynamic_payload["items"][0]["section"] is None
    assert dynamic_payload["groups"] == [{"key": "get-/items", "count": 1}]


def test_constraint_explorer_endpoints_support_querying_facets_and_detail(tmp_path):
    client = _client(tmp_path)

    entries_response = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={
            "source": "combined",
            "operation_id": "get-/items",
            "sort_by": "property_path",
            "group_by": "source",
        },
    )

    assert entries_response.status_code == 200
    payload = entries_response.json()
    assert payload["metadata"] == {"combined_source": "artifact", "warnings": []}
    assert payload["pagination"]["total"] == 2
    assert payload["groups"] == [{"key": "combined", "count": 2}]

    entry = next(
        item for item in payload["items"] if item["property_path"] == "return.items[].id"
    )
    assert entry["source"] == "combined"
    assert entry["constraint_kind"] == "bounds"
    assert entry["agreement_status"] == "both_present"
    assert entry["has_static"] is True
    assert entry["has_dynamic"] is True
    assert entry["assertion_available"] is True
    assert entry["assertion_preview"] == "pm.expect(return_items_id).to.be.at.least(1)"

    detail_response = client.get(
        f"/api/v1/runs/Run%20A/constraints/entries/{entry['constraint_id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["assertion"] == (
        "pm.expect(return_items_id).to.be.at.least(1)"
    )

    facets_response = client.get(
        "/api/v1/runs/Run%20A/constraints/facets",
        params={"operation_id": "get-/items"},
    )
    assert facets_response.status_code == 200
    facets = facets_response.json()
    assert {"key": "combined", "count": 2} in facets["source"]
    assert {"key": "request_response_relation", "count": 1} in facets[
        "constraint_kind"
    ]


def test_constraint_explorer_returns_400_for_invalid_business_fields(tmp_path):
    client = _client(tmp_path)

    invalid_source_response = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={"source": "invalid"},
    )
    invalid_sort_response = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={"sort_by": "missing"},
    )
    invalid_group_response = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={"group_by": "missing"},
    )
    numeric_validation_response = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={"limit": 0},
    )

    assert invalid_source_response.status_code == 400
    assert invalid_source_response.json()["error"]["code"] == "invalid_request"
    assert "source" in invalid_source_response.json()["error"]["message"]
    assert invalid_sort_response.status_code == 400
    assert "sort_by" in invalid_sort_response.json()["error"]["message"]
    assert invalid_group_response.status_code == 400
    assert "group_by" in invalid_group_response.json()["error"]["message"]
    assert numeric_validation_response.status_code == 422


def test_constraint_explorer_returns_404_for_missing_run(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/v1/runs/Missing%20Run/constraints/entries")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_detailed_invariant_graph_and_report_endpoints_support_querying(tmp_path):
    client = _client(tmp_path)

    invariants_response = client.get(
        "/api/v1/runs/Run%20A/constraints/dynamic/invariants",
        params={
            "operation_id": "get-/items",
            "invariant_type": "daikon.inv.unary.scalar.LowerBound",
            "q": "return.items.id",
            "group_by": "operation_id",
        },
    )
    graph_response = client.get(
        "/api/v1/runs/Run%20A/graph/edges",
        params={"q": "post-/items", "group_by": "from_node"},
    )
    report_response = client.get(
        "/api/v1/runs/Run%20A/reports/entries",
        params={"status_code": "404", "group_by": "status_code"},
    )

    assert invariants_response.status_code == 200
    invariants_payload = invariants_response.json()
    assert invariants_payload["pagination"]["total"] == 1
    assert invariants_payload["items"][0]["operation_id"] == "get-/items"
    assert invariants_payload["groups"] == [{"key": "get-/items", "count": 1}]

    assert graph_response.status_code == 200
    graph_payload = graph_response.json()
    assert graph_payload["pagination"]["total"] == 1
    assert graph_payload["items"][0]["from_node"] == "post-/items"
    assert graph_payload["groups"] == [{"key": "post-/items", "count": 1}]

    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["pagination"]["total"] == 1
    assert report_payload["items"][0]["status_code"] == "404"
    assert report_payload["groups"] == [{"key": "404", "count": 1}]


def test_detailed_endpoints_return_400_for_invalid_sort_and_group(tmp_path):
    client = _client(tmp_path)

    invalid_sort_response = client.get(
        "/api/v1/runs/Run%20A/constraints/static/entries",
        params={"sort_by": "missing"},
    )
    invalid_group_response = client.get(
        "/api/v1/runs/Run%20A/reports/entries",
        params={"group_by": "missing"},
    )

    assert invalid_sort_response.status_code == 400
    assert invalid_sort_response.json()["error"]["code"] == "invalid_request"
    assert "sort_by" in invalid_sort_response.json()["error"]["message"]
    assert invalid_group_response.status_code == 400
    assert invalid_group_response.json()["error"]["code"] == "invalid_request"
    assert "group_by" in invalid_group_response.json()["error"]["message"]


def test_test_cases_endpoint_defaults_to_body_omission(tmp_path):
    client = _client(tmp_path)

    response = client.get(
        "/api/v1/runs/Run%20A/test-cases",
        params={"operation_id": "get-/items", "status_code": 200},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["response_body"] is None


def test_har_sessions_and_entries_redact_by_default(tmp_path):
    client = _client(tmp_path)

    sessions_response = client.get("/api/v1/runs/Run%20A/history/sessions")
    entries_response = client.get(
        "/api/v1/runs/Run%20A/history/sessions/session-1/entries"
    )

    assert sessions_response.status_code == 200
    assert sessions_response.json()["sessions"][0]["session_id"] == "session-1"
    assert entries_response.status_code == 200
    entry = entries_response.json()["items"][0]
    assert entry["request_headers"]["authorization"] == "<REDACTED>"
    assert entry["response_body"] is None


def test_artifact_content_returns_typed_raw_content(tmp_path):
    client = _client(tmp_path)

    summarized_response = client.get(
        "/api/v1/runs/Run%20A/artifacts/specification/content"
    )
    raw_response = client.get(
        "/api/v1/runs/Run%20A/artifacts/specification/content",
        params={"raw": "true"},
    )

    assert summarized_response.status_code == 200
    assert summarized_response.json()["raw"] is False
    assert raw_response.status_code == 200
    assert raw_response.json()["raw"] is True
    assert raw_response.json()["content"]["content_kind"] in {
        "raw_json",
        "raw_text",
    }


def test_invariant_graph_and_operation_explorer_api_endpoints(tmp_path):
    client = _explorer_client(tmp_path)

    invariant_response = client.get(
        "/api/v1/runs/Run%20A/constraints/invariants",
        params={
            "operation_id": "get-/items",
            "invariant_kind": "bounds",
            "group_by": "oracle_readiness",
            "sort_by": "primary_property_path",
        },
    )
    assert invariant_response.status_code == 200
    invariant_payload = invariant_response.json()
    assert invariant_payload["pagination"]["total"] == 1
    invariant = invariant_payload["items"][0]
    assert invariant["invariant_id"].startswith("inv_")
    assert invariant["oracle_readiness"] == "schema_supported"
    assert invariant["correlation_confidence"] == "exact"
    assert invariant["related_constraint_ids"]
    assert invariant["postman_assertion"] is None

    invariant_detail_response = client.get(
        f"/api/v1/runs/Run%20A/constraints/invariants/{invariant['invariant_id']}"
    )
    assert invariant_detail_response.status_code == 200
    assert invariant_detail_response.json()["postman_assertion"] == (
        "pm.expect(return_items_id).to.be.at.least(1)"
    )

    invariant_facets_response = client.get(
        "/api/v1/runs/Run%20A/constraints/invariants/facets",
        params={"operation_id": "get-/items"},
    )
    assert invariant_facets_response.status_code == 200
    assert {"key": "schema_supported", "count": 1} in invariant_facets_response.json()[
        "oracle_readiness"
    ]

    graph_edges_response = client.get(
        "/api/v1/runs/Run%20A/graph/edges",
        params={"edge_status": "all", "group_by": "edge_status"},
    )
    assert graph_edges_response.status_code == 200
    graph_payload = graph_edges_response.json()
    assert graph_payload["pagination"]["total"] == 2
    assert {"key": "candidate", "count": 1} in graph_payload["groups"]
    edge = next(item for item in graph_payload["items"] if item["edge_status"] == "candidate")
    assert edge["evidence_count"] == 1
    assert edge["evidence_sources"] == ["gpt_edges"]

    edge_detail_response = client.get(
        f"/api/v1/runs/Run%20A/graph/edges/{edge['edge_id']}"
    )
    assert edge_detail_response.status_code == 200
    assert edge_detail_response.json()["evidence"][0]["source"] == "gpt_edges"

    graph_nodes_response = client.get(
        "/api/v1/runs/Run%20A/graph/nodes",
        params={"node_kind": "parameter"},
    )
    assert graph_nodes_response.status_code == 200
    assert any(
        node["parameter_name"] == "limit"
        for node in graph_nodes_response.json()["items"]
    )

    graph_sequences_response = client.get(
        "/api/v1/runs/Run%20A/graph/sequences",
        params={"target_operation_id": "get-/items"},
    )
    assert graph_sequences_response.status_code == 200
    sequence = graph_sequences_response.json()["items"][0]
    assert sequence["operations"] == ["post-/items", "get-/items"]
    assert sequence["sequence_type"] == "producer-path"

    operation_response = client.get(
        "/api/v1/runs/Run%20A/operations/entries",
        params={"has_constraints": "true", "sort_by": "operation_id"},
    )
    assert operation_response.status_code == 200
    operation = next(
        item
        for item in operation_response.json()["items"]
        if item["operation_id"] == "get-/items"
    )
    assert operation["operation_key"].startswith("op_")
    assert operation["constraint_count"] >= 1
    assert operation["invariant_count"] == 1
    assert operation["has_failures"] is True

    operation_detail_response = client.get(
        f"/api/v1/runs/Run%20A/operations/entries/{operation['operation_key']}"
    )
    assert operation_detail_response.status_code == 200
    assert operation_detail_response.json()["related_invariant_ids"]


def test_explorer_api_returns_400_for_invalid_business_fields(tmp_path):
    client = _explorer_client(tmp_path)

    invalid_invariant_response = client.get(
        "/api/v1/runs/Run%20A/constraints/invariants",
        params={"invariant_kind": "missing"},
    )
    invalid_graph_response = client.get(
        "/api/v1/runs/Run%20A/graph/edges",
        params={"edge_status": "missing"},
    )
    invalid_operation_response = client.get(
        "/api/v1/runs/Run%20A/operations/entries",
        params={"sort_by": "missing"},
    )
    numeric_validation_response = client.get(
        "/api/v1/runs/Run%20A/graph/nodes",
        params={"limit": 0},
    )

    assert invalid_invariant_response.status_code == 400
    assert invalid_graph_response.status_code == 400
    assert invalid_operation_response.status_code == 400
    assert numeric_validation_response.status_code == 422


def test_raw_test_case_artifact_sanitizes_sensitive_bodies(tmp_path):
    client = _client(tmp_path)

    response = client.get(
        "/api/v1/runs/Run%20A/artifacts/test_cases_json/content",
        params={"raw": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    payload_text = json.dumps(payload)
    assert payload["content"]["content_kind"] == "sanitized_test_cases"
    assert "test-client-secret" not in payload_text
    assert "test-response-token" not in payload_text
    assert payload["content"]["items"][1]["request_body"]["redaction_count"] >= 1
    assert payload["content"]["items"][1]["response_body"]["redaction_count"] >= 1


def test_raw_har_artifact_sanitizes_headers_and_bodies(tmp_path):
    client = _client(tmp_path)

    response = client.get(
        "/api/v1/runs/Run%20A/artifacts/history_session-1/content",
        params={"raw": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    payload_text = json.dumps(payload)
    assert payload["content"]["content_kind"] == "sanitized_har_session"
    assert "Bearer test-secret" not in payload_text
    assert "session=secret" not in payload_text
    assert "test-password" not in payload_text
    assert "test-access-token" not in payload_text
    entry = payload["content"]["entries"][0]
    assert entry["request_headers"]["authorization"] == "<REDACTED>"
    assert entry["response_headers"]["set-cookie"] == "<REDACTED>"
    assert entry["request_body"]["redaction_count"] >= 1
    assert entry["response_body"]["redaction_count"] >= 1


def test_missing_run_uses_typed_error_response(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/v1/runs/missing/summary")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "missing" in response.json()["error"]["message"]


def test_invalid_query_params_return_fastapi_validation_errors(tmp_path):
    client = _client(tmp_path)

    limit_response = client.get(
        "/api/v1/runs/Run%20A/test-cases",
        params={"limit": 0},
    )
    status_response = client.get(
        "/api/v1/runs/Run%20A/test-cases",
        params={"status_code": 99},
    )

    assert limit_response.status_code == 422
    assert status_response.status_code == 422


def test_unknown_har_session_uses_typed_error_response(tmp_path):
    client = _client(tmp_path)

    response = client.get(
        "/api/v1/runs/Run%20A/history/sessions/missing/entries"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
