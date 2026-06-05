from __future__ import annotations

import json

from tests.fixtures.backend_artifacts import build_artifact_cache


def test_openapi_contains_planned_paths(tmp_path):
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    app = create_app(BackendSettings(cache_root=build_artifact_cache(tmp_path)))

    schema = app.openapi()

    for path in [
        "/api/v1/runs",
        "/api/v1/runs/{run_name}",
        "/api/v1/runs/{run_name}/summary",
        "/api/v1/runs/{run_name}/artifacts",
        "/api/v1/runs/{run_name}/operations",
        "/api/v1/runs/{run_name}/operations/entries",
        "/api/v1/runs/{run_name}/operations/entries/{operation_key}",
        "/api/v1/runs/{run_name}/operations/facets",
        "/api/v1/runs/{run_name}/operation",
        "/api/v1/runs/{run_name}/reports",
        "/api/v1/runs/{run_name}/reports/entries",
        "/api/v1/runs/{run_name}/graph",
        "/api/v1/runs/{run_name}/graph/nodes",
        "/api/v1/runs/{run_name}/graph/edges",
        "/api/v1/runs/{run_name}/graph/edges/{edge_id}",
        "/api/v1/runs/{run_name}/graph/sequences",
        "/api/v1/runs/{run_name}/graph/sequences/{sequence_id}",
        "/api/v1/runs/{run_name}/graph/facets",
        "/api/v1/runs/{run_name}/constraints/static",
        "/api/v1/runs/{run_name}/constraints/static/entries",
        "/api/v1/runs/{run_name}/constraints/entries",
        "/api/v1/runs/{run_name}/constraints/entries/{constraint_id}",
        "/api/v1/runs/{run_name}/constraints/facets",
        "/api/v1/runs/{run_name}/constraints/combination/summary",
        "/api/v1/runs/{run_name}/constraints/combination/entries",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}/review",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}/review/finalize",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}/review/reopen",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}/counter-examples/generate",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}/counter-examples/{case_id}",
        "/api/v1/runs/{run_name}/constraints/combination/entries/{combination_id}/counter-examples/run",
        "/api/v1/runs/{run_name}/constraints/combination/counter-examples/batch-generate",
        "/api/v1/runs/{run_name}/constraints/combination/facets",
        "/api/v1/runs/{run_name}/constraints/research/summary",
        "/api/v1/runs/{run_name}/constraints/research/entries",
        "/api/v1/runs/{run_name}/constraints/research/entries/{combination_id}",
        "/api/v1/runs/{run_name}/constraints/research/entries/{combination_id}/labels",
        "/api/v1/runs/{run_name}/constraints/research/labels.csv",
        "/api/v1/runs/{run_name}/constraints/invariants",
        "/api/v1/runs/{run_name}/constraints/invariants/facets",
        "/api/v1/runs/{run_name}/constraints/invariants/{invariant_id}",
        "/api/v1/runs/{run_name}/constraints/dynamic",
        "/api/v1/runs/{run_name}/constraints/dynamic/entries",
        "/api/v1/runs/{run_name}/constraints/dynamic/invariants",
        "/api/v1/runs/{run_name}/test-cases",
        "/api/v1/runs/{run_name}/history/sessions",
        "/api/v1/runs/{run_name}/history/sessions/{session_id}/entries",
        "/api/v1/runs/{run_name}/artifacts/{artifact_id}/content",
        "/api/v1/specs",
        "/api/v1/specs/{spec_id}",
        "/api/v1/specs/{spec_id}/operations",
        "/api/v1/run-configs",
        "/api/v1/run-configs/validate",
        "/api/v1/run-configs/{run_config_id}",
        "/api/v1/executions",
        "/api/v1/executions/{execution_id}",
        "/api/v1/executions/{execution_id}/cancel",
        "/api/v1/executions/{execution_id}/events",
        "/api/v1/executions/{execution_id}/run",
        "/health",
    ]:
        assert path in schema["paths"]


def test_openapi_contains_typed_detailed_response_schemas(tmp_path):
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    app = create_app(BackendSettings(cache_root=build_artifact_cache(tmp_path)))

    schema = app.openapi()
    components = schema["components"]["schemas"]

    for schema_name in [
        "ConstraintEntryPageResponse",
        "ConstraintEntryDetailResponse",
        "ConstraintExplorerEntryResponse",
        "ConstraintExplorerDetailResponse",
        "ConstraintExplorerPageResponse",
        "ConstraintFacetsResponse",
        "ConstraintQueryMetadataResponse",
        "CombinationSummaryResponse",
        "CombinationEntryResponse",
        "CombinationDetailResponse",
        "CombinationEntryPageResponse",
        "CombinationFacetsResponse",
        "CombinationReviewResponse",
        "CounterExampleCaseResponse",
        "CounterExampleRunRequest",
        "CombinationReviewFinalizeRequest",
        "BatchCounterExampleGenerateRequest",
        "BatchCounterExampleGenerateResponse",
        "ConstraintResearchSummaryResponse",
        "ConstraintResearchEntryResponse",
        "ConstraintResearchEntryPageResponse",
        "ConstraintResearchDetailResponse",
        "ConstraintResearchEvidenceCaseResponse",
        "ConstraintResearchLabelUpdateRequest",
        "InvariantExplorerEntryResponse",
        "InvariantExplorerDetailResponse",
        "InvariantExplorerPageResponse",
        "InvariantExplorerFacetsResponse",
        "InvariantPageResponse",
        "InvariantDetailResponse",
        "GraphNodeResponse",
        "GraphNodePageResponse",
        "GraphEdgeDetailResponse",
        "GraphEdgePageResponse",
        "GraphFacetsResponse",
        "GraphSequenceResponse",
        "GraphSequencePageResponse",
        "OperationExplorerEntryResponse",
        "OperationExplorerDetailResponse",
        "OperationExplorerPageResponse",
        "OperationFacetsResponse",
        "ReportEntryPageResponse",
        "SpecMetadataResponse",
        "SpecOperationsResponse",
        "RunConfigResponse",
        "RunConfigValidationResponse",
        "ExecutionResponse",
        "ExecutionEventListResponse",
        "GroupCountResponse",
    ]:
        assert schema_name in components


def test_openapi_describes_dynamic_constraints_and_raw_invariants(tmp_path):
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    app = create_app(BackendSettings(cache_root=build_artifact_cache(tmp_path)))

    schema = app.openapi()
    components = schema["components"]["schemas"]

    dynamic_properties = components["DynamicConstraintsResponse"]["properties"]
    operation_properties = components["OperationExplorerEntryResponse"]["properties"]
    dynamic_route = schema["paths"][
        "/api/v1/runs/{run_name}/constraints/dynamic"
    ]["get"]
    operation_params = schema["paths"][
        "/api/v1/runs/{run_name}/operations/entries"
    ]["get"]["parameters"]
    has_invariants_param = next(
        param for param in operation_params if param["name"] == "has_invariants"
    )

    assert "mapped dynamic constraints" in dynamic_route["description"]
    assert "raw invariant" in dynamic_route["description"]
    assert "mapped dynamic" in dynamic_properties["constraint_count"]["description"]
    assert "raw Daikon invariant" in dynamic_properties["invariant_count"]["description"]
    assert (
        "raw daikon invariant"
        in operation_properties["invariant_count"]["description"].lower()
    )
    assert "raw invariant row" in has_invariants_param["description"]


def test_openapi_exposes_combination_relation_contract(tmp_path):
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    app = create_app(BackendSettings(cache_root=build_artifact_cache(tmp_path)))

    schema = app.openapi()
    components = schema["components"]["schemas"]
    entry_properties = components["CombinationEntryResponse"]["properties"]
    explorer_properties = components["ConstraintExplorerEntryResponse"]["properties"]
    explorer_facet_properties = components["ConstraintFacetsResponse"]["properties"]
    review_properties = components["CombinationReviewResponse"]["properties"]
    batch_item_properties = components["BatchCounterExampleGenerateItemResponse"]["properties"]
    run_request_properties = components["CounterExampleRunRequest"]["properties"]
    summary_properties = components["CombinationSummaryResponse"]["properties"]
    facet_properties = components["CombinationFacetsResponse"]["properties"]
    entry_params = schema["paths"][
        "/api/v1/runs/{run_name}/constraints/combination/entries"
    ]["get"]["parameters"]
    param_names = {param["name"] for param in entry_params}

    assert "relation" in entry_properties
    assert "runtime_verdict" in entry_properties
    assert "review_state" in entry_properties
    assert "decision_source" in entry_properties
    assert "has_manual_decision" in entry_properties
    assert "target_base_url_suggestions" in review_properties
    assert "new_case_count" in batch_item_properties
    assert "total_case_count" in batch_item_properties
    assert "base_url" not in components["CounterExampleRunRequest"]["required"]
    assert "combination_id" in explorer_properties
    assert "review_state" in explorer_properties
    assert "decision_source" in explorer_properties
    assert "has_manual_decision" in explorer_properties
    assert "manual_decision" in explorer_properties
    assert "manual_final_constraint" in explorer_properties
    assert "review_state" in explorer_facet_properties
    assert "decision_source" in explorer_facet_properties
    assert "has_manual_decision" in explorer_facet_properties
    assert "manual_decision" in explorer_facet_properties
    assert "base_url" in run_request_properties
    assert "verdict" not in entry_properties
    assert "relation_counts" in summary_properties
    assert "runtime_verdict_counts" in summary_properties
    assert "relation" in facet_properties
    assert "runtime_verdict" in facet_properties
    assert "review_state" in facet_properties
    assert "decision_source" in facet_properties
    assert "has_manual_decision" in facet_properties
    assert "relation" in param_names
    assert "runtime_verdict" in param_names
    assert "review_state" in param_names
    assert "decision_source" in param_names
    assert "has_manual_decision" in param_names
    assert "verdict" not in param_names


def test_export_openapi_writes_deterministic_json(tmp_path, monkeypatch):
    from api_testing.backend.export_openapi import export_openapi
    from api_testing.backend.settings import BackendSettings

    output_path = tmp_path / "openapi.json"
    monkeypatch.setenv(
        "APIPILOT_BACKEND_CACHE_ROOT",
        str(build_artifact_cache(tmp_path)),
    )

    export_openapi(output_path, settings=BackendSettings.from_env())

    exported = json.loads(output_path.read_text(encoding="utf-8"))
    assert exported["openapi"].startswith("3.")
    assert "/api/v1/runs" in exported["paths"]
    assert output_path.read_text(encoding="utf-8").endswith("\n")
