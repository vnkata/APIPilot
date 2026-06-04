from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.fakes.http import FakeJsonResponse
from tests.fixtures.backend_artifacts import build_artifact_cache, write_json


def _client(tmp_path: Path, cache_root: Path) -> TestClient:
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    settings = BackendSettings(
        cache_root=cache_root,
        metadata_db_path=tmp_path / "backend.db",
        allowed_target_base_urls=("https://example.test",),
        default_execution_timeout_seconds=5,
        default_request_budget=5,
    )
    return TestClient(create_app(settings))


def _cache_with_reviewable_combination(tmp_path: Path) -> Path:
    cache_root = build_artifact_cache(tmp_path)
    run_dir = cache_root / "Run A"
    write_json(
        run_dir / "combine_constraint_miners.json",
        {
            "get-/items": {
                "return.item_count": {
                    "endpoint": "get-/items",
                    "property": "return.item_count",
                    "static_constraint": "gte(return.item_count, 0)",
                    "dynamic_constraint": "return.item_count == 5",
                    "status": "UNRESOLVED",
                    "relation": "DYNAMIC_STRONGER",
                    "runtime_verdict": None,
                    "final_constraint": None,
                    "reason": "Needs human review.",
                    "counter_example": {
                        "staged_payload": {
                            "endpoint_path": "/items",
                            "http_method": "post",
                            "headers": {"Authorization": "Bearer fixture-secret"},
                            "parameters": {"limit": 5},
                            "body": {"client_secret": "fixture-body-secret"},
                        }
                    },
                    "validation_cases": [],
                },
                "return.items[].id": {
                    "endpoint": "get-/items",
                    "property": "return.items[].id",
                    "static_constraint": "gte(return.items[].id, 1)",
                    "dynamic_constraint": "return.items.id >= 1",
                    "status": "RESOLVED",
                    "relation": "EQUIVALENT",
                    "runtime_verdict": "BOTH_TRUE",
                    "final_constraint": "gte(return.items[].id, 1)",
                    "reason": "Already resolved.",
                },
            }
        },
    )
    return cache_root


def _combination_id(client: TestClient, *, relation: str = "DYNAMIC_STRONGER") -> str:
    response = client.get(
        "/api/v1/runs/Run%20A/constraints/combination/entries",
        params={"relation": relation},
    )
    assert response.status_code == 200
    return response.json()["items"][0]["combination_id"]


def test_combination_entries_overlay_default_review_state(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)

    response = client.get("/api/v1/runs/Run%20A/constraints/combination/entries")

    assert response.status_code == 200
    payload = response.json()
    reviewable = next(
        item for item in payload["items"] if item["relation"] == "DYNAMIC_STRONGER"
    )
    assert reviewable["review_state"] == "PENDING_REVIEW"
    assert reviewable["decision_source"] is None
    assert reviewable["has_manual_decision"] is False
    facets = client.get("/api/v1/runs/Run%20A/constraints/combination/facets").json()
    assert {"key": "PENDING_REVIEW", "count": 2} in facets["review_state"]
    assert {"key": "false", "count": 2} in facets["has_manual_decision"]


def test_review_generate_approve_run_finalize_and_reopen(tmp_path, monkeypatch):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    calls = []

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, "kwargs": kwargs})
        return FakeJsonResponse(
            {"item_count": 5, "access_token": "response-secret"},
            headers={"Content-Type": "application/json", "Set-Cookie": "secret-cookie"},
        )

    monkeypatch.setattr("requests.request", fake_request)

    review_response = client.get(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review"
    )
    assert review_response.status_code == 200
    assert review_response.json()["review_state"] == "PENDING_REVIEW"

    generate_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={
            "live_llm": False,
            "idempotency_key": "generate-fallback-1",
            "max_cases": 1,
        },
    )
    assert generate_response.status_code == 201
    generated = generate_response.json()
    assert generated["review_state"] == "DRAFT_READY"
    case = generated["cases"][0]
    assert case["case_state"] == "DRAFT"
    assert "fixture-secret" not in json.dumps(generated)
    assert "fixture-body-secret" not in json.dumps(generated)

    approve_response = client.put(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/{case['case_id']}",
        json={
            "case_state": "APPROVED",
            "rationale": "Safe local approval.",
            "request": {
                "method": "POST",
                "path": "/items",
                "query": {"limit": 5},
                "body": {"safe": "visible"},
            },
        },
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["review_state"] == "APPROVED"

    blocked_run = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/run",
        json={
            "live_api": True,
            "base_url": "https://example.test",
            "request_budget": 3,
            "timeout_seconds": 5,
            "idempotency_key": "run-blocked-1",
        },
    )
    assert blocked_run.status_code == 400
    assert "confirmation" in blocked_run.json()["error"]["message"]

    run_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/run",
        json={
            "live_api": True,
            "base_url": "https://example.test",
            "request_budget": 3,
            "timeout_seconds": 5,
            "unsafe_method_confirmed": True,
            "idempotency_key": "run-approved-1",
        },
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert calls[0]["method"] == "post"
    assert run_payload["review_state"] == "RUN_COMPLETED"
    assert run_payload["runtime_recommendation"] == "INCONCLUSIVE"
    assert "response-secret" not in json.dumps(run_payload)

    finalize_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review/finalize",
        json={
            "manual_decision": "CUSTOM_FINAL",
            "idempotency_key": "finalize-1",
            "custom_final_constraint": "gte(return.item_count, 0)",
            "rationale": "Business accepts the static lower bound.",
        },
    )
    assert finalize_response.status_code == 200
    finalized = finalize_response.json()
    assert finalized["review_state"] == "FINAL_CONFIRMED"
    assert finalized["decision_source"] == "human"
    assert finalized["has_manual_decision"] is True

    sidecar = json.loads(
        (cache_root / "Run A" / "counter_example_reviews.json").read_text("utf-8")
    )
    assert finalized["review_key"] in sidecar["reviews"]
    original_artifact = json.loads(
        (cache_root / "Run A" / "combine_constraint_miners.json").read_text("utf-8")
    )
    assert original_artifact["get-/items"]["return.item_count"]["final_constraint"] is None

    reopen_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review/reopen",
        json={"rationale": "Need another review pass."},
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["review_state"] == "REOPENED"


def test_finalize_requires_rationale_and_custom_final_constraint(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    missing_rationale = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review/finalize",
        json={"manual_decision": "ACCEPT_STATIC", "idempotency_key": "missing-rationale"},
    )
    missing_custom = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review/finalize",
        json={
            "manual_decision": "CUSTOM_FINAL",
            "idempotency_key": "missing-custom",
            "rationale": "Need custom.",
        },
    )

    assert missing_rationale.status_code == 422
    assert missing_custom.status_code == 422


def test_batch_generate_only_creates_drafts_for_eligible_rows(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    eligible_id = _combination_id(client)
    resolved_id = _combination_id(client, relation="EQUIVALENT")

    response = client.post(
        "/api/v1/runs/Run%20A/constraints/combination/counter-examples/batch-generate",
        json={
            "combination_ids": [eligible_id, resolved_id],
            "live_llm": False,
            "idempotency_key": "batch-fallback-1",
            "max_items": 10,
            "max_cases_per_item": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    results = {item["combination_id"]: item for item in payload["results"]}
    assert results[eligible_id]["status"] == "generated"
    assert results[eligible_id]["case_count"] == 1
    assert results[eligible_id]["new_case_count"] == 1
    assert results[eligible_id]["total_case_count"] == 1
    assert results[resolved_id]["status"] == "skipped"
    assert results[resolved_id]["new_case_count"] == 0
    assert results[resolved_id]["total_case_count"] == 0
    assert "not eligible" in results[resolved_id]["message"]


def test_live_llm_generate_persists_planner_fields_and_replays_idempotently(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    class FakePlanner:
        prompt_version = "fake-planner-v1"

        def __init__(self):
            self.calls = []
            self.last_error = None

        def generate(self, context):
            self.calls.append(context)
            return [
                {
                    "case_id": "planner-case-1",
                    "request": {
                        "method": "GET",
                        "path": "/items",
                        "path_parameters": {},
                        "query": {"limit": 5},
                        "headers": {"Authorization": "Bearer fake-secret"},
                        "body": None,
                    },
                    "target_truth_vector": {
                        "static_constraint": "true",
                        "dynamic_constraint": "false",
                    },
                    "rationale": "Probe a static-only branch.",
                    "risk": "low",
                    "expected_observation": "The response satisfies only the static constraint.",
                }
            ]

    fake_planner = FakePlanner()
    service = client.app.state.combination_review_service
    service.planner_factory = lambda: fake_planner

    payload = {
        "live_llm": True,
        "idempotency_key": "generate-live-1",
        "max_cases": 1,
    }
    first = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json=payload,
    )
    second = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert len(fake_planner.calls) == 1
    generated = second.json()
    assert generated["review_state"] == "DRAFT_READY"
    assert len(generated["cases"]) == 1
    case = generated["cases"][0]
    assert case["generation_id"].startswith("ceg_")
    assert case["request"] == {
        "method": "GET",
        "path": "/items",
        "path_parameters": {},
        "query": {"limit": 5},
        "headers": {"Authorization": {"type": "redacted", "reason": "sensitive_header"}},
    }
    assert case["request_display"] == {
        "method": "GET",
        "path": "/items",
        "path_parameters": {},
        "query": {"limit": 5},
        "headers": {"Authorization": "<REDACTED>"},
    }
    assert case["validation_error"]["raw_secret_values"]
    assert case["target_truth_vector"] == {
        "static_constraint": "true",
        "dynamic_constraint": "false",
    }
    assert case["risk"] == "low"
    assert case["expected_observation"] == (
        "The response satisfies only the static constraint."
    )
    assert case["planner_version"] == "fake-planner-v1"
    assert case["source_metadata"]["live_llm"] is True
    assert "fake-secret" not in json.dumps(generated)


def test_session_domain_query_param_survives_private_request_but_not_header_secret(tmp_path, monkeypatch):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    run_dir = cache_root / "Run A"
    spec = json.loads((run_dir / "specification.json").read_text("utf-8"))
    spec["operations"]["get-/items"]["parameters"]["Session"] = {
        "name": "Session",
        "in_value": "query",
        "schema": {"type": "string"},
    }
    write_json(run_dir / "specification.json", spec)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    class FakePlanner:
        prompt_version = "fake-planner-v1"
        last_error = None

        def generate(self, context):
            return [
                {
                    "case_id": "session-case",
                    "request": {
                        "method": "GET",
                        "path": "/items",
                        "query": {"Session": "2025", "limit": 5},
                        "headers": {"Authorization": "Bearer should-not-persist"},
                    },
                    "target_truth_vector": {
                        "static_constraint": "true",
                        "dynamic_constraint": "false",
                    },
                    "rationale": "Probe a domain Session query parameter.",
                    "risk": "low",
                    "expected_observation": "Session is a domain query parameter.",
                }
            ]

    client.app.state.combination_review_service.planner_factory = lambda: FakePlanner()
    generated = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={"live_llm": True, "idempotency_key": "session-generate-1", "max_cases": 1},
    )

    assert generated.status_code == 201
    case = generated.json()["cases"][0]
    assert case["request"]["query"]["Session"] == "2025"
    assert case["request_display"]["query"]["Session"] == "2025"
    assert case["request"]["headers"]["Authorization"] == {
        "type": "redacted",
        "reason": "sensitive_header",
    }
    assert "should-not-persist" not in json.dumps(generated.json())

    approved = client.put(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/{case['case_id']}",
        json={
            "case_state": "APPROVED",
            "rationale": "Approve domain Session value.",
            "request": {
                "method": "GET",
                "path": "/items",
                "query": {"Session": "2026", "limit": 7},
            },
        },
    )
    assert approved.status_code == 200
    approved_case = approved.json()["cases"][0]
    assert approved_case["request"]["query"]["Session"] == "2026"

    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs)
        return FakeJsonResponse({"item_count": 5})

    monkeypatch.setattr("requests.request", fake_request)
    run_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/run",
        json={
            "live_api": True,
            "base_url": "https://example.test",
            "request_budget": 1,
            "timeout_seconds": 5,
            "unsafe_method_confirmed": False,
            "idempotency_key": "session-run-1",
        },
    )

    assert run_response.status_code == 200
    assert calls[0]["params"]["Session"] == "2026"


def test_approval_rejects_redacted_executable_request_values(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    generated = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={"live_llm": False, "idempotency_key": "redacted-generate-1", "max_cases": 1},
    )
    case_id = generated.json()["cases"][0]["case_id"]
    literal_redacted = client.put(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/{case_id}",
        json={
            "case_state": "APPROVED",
            "rationale": "Legacy redacted approval.",
            "request": {
                "method": "GET",
                "path": "/items",
                "query": {"Session": "<REDACTED>"},
            },
        },
    )
    assert literal_redacted.status_code == 400
    assert "redacted executable request" in literal_redacted.json()["error"]["message"].lower()

    redacted_ref = client.put(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/{case_id}",
        json={
            "case_state": "APPROVED",
            "rationale": "Redacted ref approval.",
            "request": {
                "method": "GET",
                "path": "/items",
                "headers": {"Authorization": {"type": "redacted", "reason": "sensitive_header"}},
            },
        },
    )
    assert redacted_ref.status_code == 400
    assert "redacted executable request" in redacted_ref.json()["error"]["message"].lower()


def test_review_response_includes_target_base_url_suggestions(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    run_dir = cache_root / "Run A"
    spec = json.loads((run_dir / "specification.json").read_text("utf-8"))
    spec["servers"] = [{"url": "https://example.test"}]
    write_json(run_dir / "specification.json", spec)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    response = client.get(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review"
    )

    assert response.status_code == 200
    assert response.json()["target_base_url_suggestions"] == ["https://example.test"]


def test_run_can_resolve_base_url_from_spec_when_not_explicit(tmp_path, monkeypatch):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    run_dir = cache_root / "Run A"
    spec = json.loads((run_dir / "specification.json").read_text("utf-8"))
    spec["servers"] = [{"url": "https://example.test"}]
    write_json(run_dir / "specification.json", spec)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)
    generated = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={"live_llm": False, "idempotency_key": "base-url-generate-1", "max_cases": 1},
    )
    case_id = generated.json()["cases"][0]["case_id"]
    approved = client.put(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/{case_id}",
        json={
            "case_state": "APPROVED",
            "rationale": "Approve spec base URL case.",
            "request": {"method": "GET", "path": "/items", "query": {"limit": 1}},
        },
    )
    assert approved.status_code == 200

    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(url)
        return FakeJsonResponse({"item_count": 5})

    monkeypatch.setattr("requests.request", fake_request)
    run_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/run",
        json={
            "live_api": True,
            "request_budget": 1,
            "timeout_seconds": 5,
            "idempotency_key": "base-url-run-1",
        },
    )

    assert run_response.status_code == 200
    assert calls == ["https://example.test/items"]


def test_run_resolves_typed_env_secret_refs_at_execution_time(tmp_path, monkeypatch):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)
    generated = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={"live_llm": False, "idempotency_key": "secret-ref-generate-1", "max_cases": 1},
    )
    case_id = generated.json()["cases"][0]["case_id"]
    approved = client.put(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/{case_id}",
        json={
            "case_state": "APPROVED",
            "rationale": "Approve typed secret ref.",
            "request": {
                "method": "GET",
                "path": "/items",
                "headers": {"Authorization": {"type": "env", "name": "APIPILOT_TEST_TOKEN"}},
                "query": {"limit": 1},
            },
        },
    )
    assert approved.status_code == 200
    assert approved.json()["cases"][0]["request_display"]["headers"]["Authorization"] == "<REDACTED>"

    missing = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/run",
        json={
            "live_api": True,
            "base_url": "https://example.test",
            "request_budget": 1,
            "timeout_seconds": 5,
            "idempotency_key": "secret-ref-run-missing",
        },
    )
    assert missing.status_code == 400
    assert "secret ref" in missing.json()["error"]["message"].lower()

    monkeypatch.setenv("APIPILOT_TEST_TOKEN", "Bearer resolved-token")

    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs)
        return FakeJsonResponse({"item_count": 5})

    monkeypatch.setattr("requests.request", fake_request)
    run_response = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/run",
        json={
            "live_api": True,
            "base_url": "https://example.test",
            "request_budget": 1,
            "timeout_seconds": 5,
            "idempotency_key": "secret-ref-run-ok",
        },
    )

    assert run_response.status_code == 200
    assert calls[0]["headers"]["Authorization"] == "Bearer resolved-token"
    assert "resolved-token" not in json.dumps(run_response.json())


def test_generate_idempotency_conflict_and_append_generation_batch(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    first = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={
            "live_llm": False,
            "idempotency_key": "append-1",
            "max_cases": 1,
        },
    )
    conflict = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={
            "live_llm": False,
            "idempotency_key": "append-1",
            "max_cases": 2,
        },
    )
    second_batch = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/counter-examples/generate",
        json={
            "live_llm": False,
            "idempotency_key": "append-2",
            "max_cases": 1,
        },
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert "idempotency" in conflict.json()["error"]["message"].lower()
    assert second_batch.status_code == 201
    cases = second_batch.json()["cases"]
    assert len(cases) == 2
    assert len({case["generation_id"] for case in cases}) == 2


def test_constraint_explorer_overlays_manual_decisions(tmp_path):
    cache_root = _cache_with_reviewable_combination(tmp_path)
    client = _client(tmp_path, cache_root)
    combination_id = _combination_id(client)

    finalized = client.post(
        f"/api/v1/runs/Run%20A/constraints/combination/entries/{combination_id}/review/finalize",
        json={
            "manual_decision": "CUSTOM_FINAL",
            "idempotency_key": "explorer-finalize-1",
            "custom_final_constraint": "return.item_count >= 0",
            "rationale": "Reviewer accepts an explicit lower bound.",
        },
    )
    assert finalized.status_code == 200

    explorer = client.get(
        "/api/v1/runs/Run%20A/constraints/entries",
        params={
            "source": "combined",
            "property_path": "return.item_count",
            "has_manual_decision": True,
        },
    )
    assert explorer.status_code == 200
    payload = explorer.json()
    assert payload["items"][0]["expression"] == "return.item_count >= 0"
    assert payload["items"][0]["combination_id"] == combination_id
    assert payload["items"][0]["review_state"] == "FINAL_CONFIRMED"
    assert payload["items"][0]["decision_source"] == "human"
    assert payload["items"][0]["manual_decision"] == "CUSTOM_FINAL"
    assert payload["items"][0]["manual_final_constraint"] == "return.item_count >= 0"

    facets = client.get(
        "/api/v1/runs/Run%20A/constraints/facets",
        params={"source": "combined", "has_manual_decision": True},
    )
    assert facets.status_code == 200
    assert {"key": "CUSTOM_FINAL", "count": 1} in facets.json()["manual_decision"]
