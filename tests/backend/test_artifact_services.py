from __future__ import annotations

from tests.fixtures.backend_artifacts import build_artifact_cache


def _service(tmp_path):
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    return ArtifactService(FileArtifactRepository(build_artifact_cache(tmp_path)))


def test_service_builds_run_summary(tmp_path):
    service = _service(tmp_path)

    summary = service.get_run_summary("Run A")

    assert summary.run_name == "Run A"
    assert summary.operation_count == 2
    assert summary.test_case_count == 2
    assert summary.har_session_count == 1
    assert summary.report_status_counts == {"200": 1, "201": 1, "404": 1}
    assert summary.available_artifacts.dynamic_constraints is True


def test_service_paginates_and_filters_test_cases_without_body_by_default(tmp_path):
    service = _service(tmp_path)

    page = service.list_test_cases(
        "Run A",
        operation_id="get-/items",
        status_code=200,
        limit=1,
        offset=0,
        include_body=False,
    )

    assert page.pagination.total == 1
    assert page.items[0].test_case_id == "tc-1"
    assert page.items[0].response_body is None


def test_service_includes_parsed_test_case_body_when_requested(tmp_path):
    service = _service(tmp_path)

    page = service.list_test_cases(
        "Run A",
        operation_id="get-/items",
        status_code=None,
        limit=10,
        offset=0,
        include_body=True,
    )

    assert page.pagination.total == 2
    assert page.items[0].response_body == {"items": [{"id": 1, "name": "alpha"}]}


def test_service_redacts_har_headers_and_omits_bodies_by_default(tmp_path):
    service = _service(tmp_path)

    page = service.list_har_entries(
        "Run A",
        session_id="session-1",
        limit=10,
        offset=0,
        include_body=False,
    )

    entry = page.items[0]
    assert page.pagination.total == 1
    assert entry.request_headers["authorization"] == "<REDACTED>"
    assert entry.response_headers["set-cookie"] == "<REDACTED>"
    assert entry.request_body is None
    assert entry.response_body is None


def test_service_includes_har_bodies_only_when_requested(tmp_path):
    service = _service(tmp_path)

    page = service.list_har_entries(
        "Run A",
        session_id="session-1",
        limit=10,
        offset=0,
        include_body=True,
    )

    assert page.items[0].request_body == {"unsafe": "body", "password": "<REDACTED>"}
    assert page.items[0].response_body == {
        "items": [{"id": 1}],
        "access_token": "<REDACTED>",
    }


def test_service_returns_typed_constraint_views(tmp_path):
    service = _service(tmp_path)

    static_constraints = service.get_static_constraints("Run A")
    dynamic_constraints = service.get_dynamic_constraints("Run A")

    static_common = next(
        section for section in static_constraints.sections if section.name == "common"
    )
    assert any(
        entry.operation_id == "get-/items"
        and entry.property_path == "return.items[].id"
        for entry in static_common.constraints
    )
    assert any(
        entry.operation_id == "get-/items"
        and entry.property_path == "return.items[].id"
        for entry in dynamic_constraints.constraints
    )
    assert dynamic_constraints.invariant_count == 1


def test_service_lists_static_constraint_entries_with_query_metadata(tmp_path):
    from api_testing.backend.application.querying import ConstraintEntryQuery, QueryOptions

    service = _service(tmp_path)

    page = service.list_static_constraint_entries(
        "Run A",
        ConstraintEntryQuery(
            options=QueryOptions(
                q="input.limit",
                group_by="section",
                limit=10,
                offset=0,
            ),
            operation_id="get-/items",
            section="request_response",
        ),
    )

    assert page.pagination.total == 1
    assert page.items[0].section == "request_response"
    assert page.items[0].property_path == "input.limit"
    assert [(group.key, group.count) for group in page.groups] == [
        ("request_response", 1)
    ]


def test_service_lists_dynamic_constraint_entries(tmp_path):
    from api_testing.backend.application.querying import ConstraintEntryQuery, QueryOptions

    service = _service(tmp_path)

    page = service.list_dynamic_constraint_entries(
        "Run A",
        ConstraintEntryQuery(
            options=QueryOptions(group_by="operation_id", limit=10, offset=0),
            operation_id="get-/items",
        ),
    )

    assert page.pagination.total == 1
    assert page.items[0].operation_id == "get-/items"
    assert page.items[0].section is None
    assert [(group.key, group.count) for group in page.groups] == [("get-/items", 1)]


def test_service_lists_invariants_with_derived_operation_id(tmp_path):
    from api_testing.backend.application.querying import InvariantQuery, QueryOptions

    service = _service(tmp_path)

    page = service.list_invariants(
        "Run A",
        InvariantQuery(
            options=QueryOptions(
                q="lowerbound",
                group_by="operation_id",
                limit=10,
                offset=0,
            ),
            operation_id="get-/items",
            invariant_type="daikon.inv.unary.scalar.LowerBound",
        ),
    )

    assert page.pagination.total == 1
    assert page.items[0].operation_id == "get-/items"
    assert page.items[0].pptname == "get-/items:::EXIT"
    assert [(group.key, group.count) for group in page.groups] == [("get-/items", 1)]


def test_service_lists_constraint_explorer_entries_from_combined_artifact(tmp_path):
    from api_testing.backend.application.querying import (
        ConstraintExplorerQuery,
        QueryOptions,
    )
    from api_testing.backend.domain.models import (
        AgreementStatus,
        CombinedSource,
        ConstraintKind,
        ConstraintSource,
    )

    service = _service(tmp_path)

    page = service.list_constraint_explorer_entries(
        "Run A",
        ConstraintExplorerQuery(
            options=QueryOptions(
                group_by="source",
                limit=10,
                offset=0,
                sort_by="property_path",
            ),
            operation_id="get-/items",
            source="combined",
        ),
    )

    assert page.metadata.combined_source == CombinedSource.ARTIFACT
    assert page.metadata.warnings == []
    assert page.pagination.total == 2
    assert [(group.key, group.count) for group in page.groups] == [("combined", 2)]

    entry = next(
        item for item in page.items if item.property_path == "return.items[].id"
    )
    assert entry.source == ConstraintSource.COMBINED
    assert entry.expression == "return.items.id >= 1"
    assert entry.constraint_kind == ConstraintKind.BOUNDS
    assert entry.has_static is True
    assert entry.has_dynamic is True
    assert entry.agreement_status == AgreementStatus.BOTH_PRESENT
    assert entry.static_expression == "return.items.id >= 1"
    assert entry.dynamic_expression == "return.items.id >= 1"
    assert entry.combined_expression == "return.items.id >= 1"
    assert entry.assertion_available is True
    assert entry.assertion_preview == "pm.expect(return_items_id).to.be.at.least(1)"

    detail = service.get_constraint_explorer_entry("Run A", entry.constraint_id)

    assert detail.constraint_id == entry.constraint_id
    assert detail.assertion == "pm.expect(return_items_id).to.be.at.least(1)"


def test_service_computes_constraint_explorer_fallback_when_combined_missing(tmp_path):
    from api_testing.backend.application.querying import (
        ConstraintExplorerQuery,
        QueryOptions,
    )
    from api_testing.backend.domain.models import AgreementStatus, CombinedSource

    cache_root = build_artifact_cache(tmp_path)
    (cache_root / "Run A" / "constraint_miner.json").unlink()
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    service = ArtifactService(FileArtifactRepository(cache_root))

    page = service.list_constraint_explorer_entries(
        "Run A",
        ConstraintExplorerQuery(
            options=QueryOptions(limit=10, offset=0),
            source="combined",
            property_path="return.items[].name",
        ),
    )

    assert page.metadata.combined_source == CombinedSource.COMPUTED_FALLBACK
    assert page.metadata.warnings == [
        "constraint_miner.json is missing; combined constraints were computed from static and dynamic artifacts."
    ]
    assert page.pagination.total == 1
    assert page.items[0].agreement_status == AgreementStatus.STATIC_ONLY
    assert page.items[0].combined_expression == "required"


def test_service_normalizes_request_response_list_constraints(tmp_path):
    from api_testing.backend.application.querying import (
        ConstraintExplorerQuery,
        QueryOptions,
    )
    from api_testing.backend.domain.models import ConstraintKind, ConstraintSource

    service = _service(tmp_path)

    page = service.list_constraint_explorer_entries(
        "Run A",
        ConstraintExplorerQuery(
            options=QueryOptions(q="input.limit", limit=10, offset=0),
            source="static",
            section="request_response",
        ),
    )

    assert page.pagination.total == 1
    assert page.items[0].source == ConstraintSource.STATIC
    assert page.items[0].property_path == "input.limit"
    assert page.items[0].parameter == "limit"
    assert page.items[0].expression == "input.limit <= return.item_count"
    assert page.items[0].constraint_kind == ConstraintKind.REQUEST_RESPONSE_RELATION
    assert page.items[0].source_type == "request_response"


def test_service_lists_constraint_explorer_facets(tmp_path):
    from api_testing.backend.application.querying import ConstraintFacetsQuery

    service = _service(tmp_path)

    facets = service.get_constraint_explorer_facets(
        "Run A",
        ConstraintFacetsQuery(operation_id="get-/items"),
    )

    assert (bucket := {item.key: item.count for item in facets.source})["combined"] == 2
    assert bucket["static"] >= 3
    assert {item.key for item in facets.constraint_kind} >= {
        "bounds",
        "request_response_relation",
        "required",
    }
    assert {item.key for item in facets.agreement_status} >= {
        "both_present",
        "static_only",
    }
    assert {item.key for item in facets.assertion_available} >= {"true", "false"}


def test_service_constraint_explorer_cache_invalidates_when_artifact_changes(tmp_path):
    from tests.fixtures.backend_artifacts import write_json

    from api_testing.backend.application.querying import (
        ConstraintExplorerQuery,
        QueryOptions,
    )

    cache_root = build_artifact_cache(tmp_path)
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    service = ArtifactService(FileArtifactRepository(cache_root))

    first_page = service.list_constraint_explorer_entries(
        "Run A",
        ConstraintExplorerQuery(
            options=QueryOptions(q="homepage", limit=10, offset=0),
            source="combined",
        ),
    )
    assert first_page.pagination.total == 0

    write_json(
        cache_root / "Run A" / "constraint_miner.json",
        {
            "get-/items": {
                "return.items[].id": "return.items.id >= 1",
                "return.items[].name": "required",
                "return.items[].homepage": "url",
            }
        },
    )

    second_page = service.list_constraint_explorer_entries(
        "Run A",
        ConstraintExplorerQuery(
            options=QueryOptions(q="homepage", limit=10, offset=0),
            source="combined",
        ),
    )

    assert second_page.pagination.total == 1
    assert second_page.items[0].property_path == "return.items[].homepage"


def test_service_parses_complex_canada_holidays_pptname_best_effort(tmp_path):
    from api_testing.backend.application.querying import InvariantQuery, QueryOptions

    service = _service(tmp_path)

    page = service.list_invariants(
        "Canada Holidays Medium",
        InvariantQuery(
            options=QueryOptions(limit=10, offset=0),
            operation_id="get-/api/v1/holidays",
        ),
    )

    assert page.pagination.total == 2
    assert {item.operation_id for item in page.items} == {"get-/api/v1/holidays"}
    assert any(
        item.pptname is not None
        and item.pptname.startswith(
            "get-/api/v1/holidays&get-/api/v1/holidays&200"
        )
        for item in page.items
    )


def test_service_lists_graph_edges_and_report_entries(tmp_path):
    from api_testing.backend.application.querying import (
        GraphEdgeQuery,
        QueryOptions,
        ReportEntryQuery,
        SortOrder,
    )

    service = _service(tmp_path)

    graph_page = service.list_graph_edges(
        "Run A",
        GraphEdgeQuery(
            options=QueryOptions(q="post-/items", group_by="from_node"),
            from_node="post-/items",
        ),
    )
    report_page = service.list_report_entries(
        "Run A",
        ReportEntryQuery(
            options=QueryOptions(
                sort_by="count",
                sort_order=SortOrder.DESC,
                group_by="status_code",
            ),
            status_code="404",
        ),
    )

    assert graph_page.pagination.total == 1
    assert graph_page.items[0].to_node == "get-/items"
    assert [(group.key, group.count) for group in graph_page.groups] == [
        ("post-/items", 1)
    ]
    assert report_page.pagination.total == 1
    assert report_page.items[0].operation_id == "get-/items"
    assert [(group.key, group.count) for group in report_page.groups] == [("404", 1)]


def test_service_lists_invariant_explorer_with_correlation_facets_and_detail(tmp_path):
    from tests.fixtures.backend_explorer_artifacts import build_explorer_artifact_cache

    from api_testing.backend.application.querying import (
        InvariantExplorerQuery,
        InvariantFacetsQuery,
        QueryOptions,
    )
    from api_testing.backend.domain.models import (
        CorrelationConfidence,
        InvariantKind,
        OracleReadiness,
    )
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    service = ArtifactService(FileArtifactRepository(build_explorer_artifact_cache(tmp_path)))

    page = service.list_invariant_explorer_entries(
        "Run A",
        InvariantExplorerQuery(
            options=QueryOptions(
                q="return.items",
                group_by="oracle_readiness",
                sort_by="primary_property_path",
                limit=10,
                offset=0,
            ),
            operation_id="get-/items",
            invariant_kind="bounds",
        ),
    )

    assert page.pagination.total == 1
    invariant = page.items[0]
    assert invariant.invariant_id.startswith("inv_")
    assert invariant.operation_id == "get-/items"
    assert invariant.property_paths == ["return.items[].id"]
    assert invariant.primary_property_path == "return.items[].id"
    assert invariant.invariant_kind == InvariantKind.BOUNDS
    assert invariant.oracle_readiness == OracleReadiness.SCHEMA_SUPPORTED
    assert invariant.assertion_available is True
    assert invariant.assertion_preview == "pm.expect(return_items_id).to.be.at.least(1)"
    assert invariant.related_constraint_ids
    assert invariant.correlation_confidence == CorrelationConfidence.EXACT
    assert invariant.correlation_evidence[0].evidence_type == "property_path"
    assert [(group.key, group.count) for group in page.groups] == [
        ("schema_supported", 1)
    ]

    detail = service.get_invariant_explorer_entry("Run A", invariant.invariant_id)
    assert detail.postman_assertion == "pm.expect(return_items_id).to.be.at.least(1)"

    facets = service.get_invariant_explorer_facets(
        "Run A",
        InvariantFacetsQuery(operation_id="get-/items"),
    )
    assert {bucket.key: bucket.count for bucket in facets.invariant_kind}["bounds"] == 1
    assert (
        {bucket.key: bucket.count for bucket in facets.oracle_readiness}[
            "schema_supported"
        ]
        == 1
    )


def test_service_lists_graph_explorer_nodes_edges_sequences_and_facets(tmp_path):
    from tests.fixtures.backend_explorer_artifacts import build_explorer_artifact_cache

    from api_testing.backend.application.querying import (
        GraphEdgeExplorerQuery,
        GraphFacetsQuery,
        GraphNodeQuery,
        GraphSequenceQuery,
        QueryOptions,
    )
    from api_testing.backend.domain.models import GraphEdgeStatus, GraphNodeKind
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    service = ArtifactService(FileArtifactRepository(build_explorer_artifact_cache(tmp_path)))

    nodes = service.list_graph_nodes(
        "Run A",
        GraphNodeQuery(
            options=QueryOptions(group_by="node_kind", limit=20, offset=0),
        ),
    )
    assert {node.node_kind for node in nodes.items} >= {
        GraphNodeKind.OPERATION,
        GraphNodeKind.PROPERTY,
        GraphNodeKind.PARAMETER,
    }
    assert any(node.parameter_name == "limit" for node in nodes.items)
    assert any(node.property_path == "return.items[].name" for node in nodes.items)

    final_edges = service.list_graph_edges(
        "Run A",
        GraphEdgeExplorerQuery(
            options=QueryOptions(group_by="edge_status", limit=10, offset=0),
        ),
    )
    assert final_edges.pagination.total == 1
    final_edge = final_edges.items[0]
    assert final_edge.edge_status == GraphEdgeStatus.FINAL
    assert final_edge.from_node == "post-/items"
    assert final_edge.to_node == "get-/items"
    assert set(final_edge.evidence_sources) == {
        "final_graph",
        "heuristic_edges",
        "gpt_edges",
    }

    all_edges = service.list_graph_edges(
        "Run A",
        GraphEdgeExplorerQuery(
            options=QueryOptions(limit=10, offset=0),
            edge_status="all",
        ),
    )
    assert {edge.edge_status for edge in all_edges.items} == {
        GraphEdgeStatus.FINAL,
        GraphEdgeStatus.CANDIDATE,
    }
    candidate = next(edge for edge in all_edges.items if edge.edge_status == GraphEdgeStatus.CANDIDATE)
    detail = service.get_graph_edge("Run A", candidate.edge_id)
    assert detail.evidence[0].source == "gpt_edges"

    sequences = service.list_graph_sequences(
        "Run A",
        GraphSequenceQuery(
            options=QueryOptions(group_by="sequence_type", limit=10, offset=0),
            target_operation_id="get-/items",
        ),
    )
    assert sequences.pagination.total == 1
    assert sequences.items[0].operations == ["post-/items", "get-/items"]
    assert sequences.items[0].sequence_type == "producer-path"

    facets = service.get_graph_facets("Run A", GraphFacetsQuery(edge_status="all"))
    edge_status_counts = {bucket.key: bucket.count for bucket in facets.edge_status}
    assert edge_status_counts["final"] == 1
    assert edge_status_counts["candidate"] == 1
    assert {bucket.key for bucket in facets.evidence_source} >= {
        "final_graph",
        "heuristic_edges",
        "gpt_edges",
    }


def test_service_parses_list_shaped_graph_sequences(tmp_path):
    from tests.fixtures.backend_explorer_artifacts import build_list_sequence_artifact_cache

    from api_testing.backend.application.querying import GraphSequenceQuery, QueryOptions
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    service = ArtifactService(
        FileArtifactRepository(build_list_sequence_artifact_cache(tmp_path))
    )

    page = service.list_graph_sequences(
        "Run A",
        GraphSequenceQuery(options=QueryOptions(limit=10, offset=0)),
    )

    assert page.pagination.total == 2
    assert {tuple(sequence.operations) for sequence in page.items} == {
        ("post-/items", "get-/items"),
        ("get-/items", "post-/items"),
    }


def test_service_lists_operation_explorer_entries_facets_and_detail(tmp_path):
    from tests.fixtures.backend_explorer_artifacts import build_explorer_artifact_cache

    from api_testing.backend.application.querying import (
        OperationExplorerQuery,
        OperationFacetsQuery,
        QueryOptions,
    )
    from api_testing.backend.repository import FileArtifactRepository
    from api_testing.backend.services import ArtifactService

    service = ArtifactService(FileArtifactRepository(build_explorer_artifact_cache(tmp_path)))

    page = service.list_operation_explorer_entries(
        "Run A",
        OperationExplorerQuery(
            options=QueryOptions(
                q="items",
                group_by="http_method",
                sort_by="operation_id",
                limit=10,
                offset=0,
            ),
            has_constraints=True,
        ),
    )

    assert page.pagination.total == 2
    get_operation = next(item for item in page.items if item.operation_id == "get-/items")
    assert get_operation.operation_key.startswith("op_")
    assert get_operation.constraint_count >= 1
    assert get_operation.invariant_count == 1
    assert get_operation.graph_in_degree == 1
    assert get_operation.graph_out_degree == 1
    assert get_operation.test_case_count == 2
    assert get_operation.has_failures is True

    detail = service.get_operation_explorer_entry("Run A", get_operation.operation_key)
    assert detail.operation_id == "get-/items"
    assert detail.report_status_counts == {"200": 1, "404": 1}
    assert detail.test_case_status_counts == {"200": 1, "404": 1}
    assert detail.related_constraint_ids
    assert detail.related_invariant_ids
    assert detail.incoming_edge_ids
    assert detail.outgoing_edge_ids

    facets = service.get_operation_explorer_facets(
        "Run A",
        OperationFacetsQuery(has_failures=True),
    )
    assert {bucket.key: bucket.count for bucket in facets.http_method}["get"] == 1
    assert {bucket.key: bucket.count for bucket in facets.has_failures}["true"] == 1
