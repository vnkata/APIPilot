from __future__ import annotations

import json

from tests.backend_artifact_fixtures import build_artifact_cache


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
