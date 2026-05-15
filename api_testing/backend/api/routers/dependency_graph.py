from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.dependency_graph import (
    DependencyGraphResponse,
    GraphEdgeDetailResponse,
    GraphEdgePageResponse,
    GraphFacetsResponse,
    GraphNodePageResponse,
    GraphSequencePageResponse,
    GraphSequenceResponse,
)
from api_testing.backend.application.querying import (
    GraphEdgeExplorerQuery,
    GraphEdgeQuery,
    GraphFacetsQuery,
    GraphNodeQuery,
    GraphSequenceQuery,
    QueryOptions,
    SortOrder,
)
from api_testing.backend.application.services import MAX_PAGE_LIMIT, ArtifactQueryService


router = APIRouter(prefix="/api/v1/runs/{run_name}", tags=["graph"])


@router.get("/graph", response_model=DependencyGraphResponse)
def get_dependency_graph(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> DependencyGraphResponse:
    return DependencyGraphResponse.from_domain(service.get_dependency_graph(run_name))


@router.get("/graph/edges", response_model=GraphEdgePageResponse)
def list_graph_edges(
    run_name: str,
    from_node: str | None = Query(default=None, description="Filter by from_node."),
    to_node: str | None = Query(default=None, description="Filter by to_node."),
    from_operation_id: str | None = Query(
        default=None,
        description="Filter by producer operation_id.",
    ),
    to_operation_id: str | None = Query(
        default=None,
        description="Filter by consumer operation_id.",
    ),
    edge_status: str | None = Query(
        default=None,
        description="Filter by edge status. Allowed values: final, candidate, all. Default is final.",
    ),
    evidence_source: str | None = Query(
        default=None,
        description="Filter by evidence source: final_graph, heuristic_edges, gpt_edges.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields across nodes, operations, status, and evidence preview.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: from_node, to_node, from_operation_id, to_operation_id, edge_status, evidence_count.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: from_node, to_node, from_operation_id, to_operation_id, edge_status.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphEdgePageResponse:
    producer = from_operation_id or from_node
    consumer = to_operation_id or to_node
    return GraphEdgePageResponse.from_domain(
        run_name,
        service.list_graph_edges(
            run_name,
            GraphEdgeExplorerQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                from_operation_id=producer,
                to_operation_id=consumer,
                edge_status=edge_status,
                evidence_source=evidence_source,
            ),
        ),
    )


@router.get("/graph/nodes", response_model=GraphNodePageResponse)
def list_graph_nodes(
    run_name: str,
    node_kind: str | None = Query(
        default=None,
        description="Filter by node kind: operation, property, parameter.",
    ),
    operation_id: str | None = Query(default=None, description="Filter by operation_id."),
    q: str | None = Query(default=None, description="Search safe graph node fields."),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: node_id, node_kind, operation_id, label, in_degree, out_degree.",
    ),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: node_kind, operation_id.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphNodePageResponse:
    return GraphNodePageResponse.from_domain(
        run_name,
        service.list_graph_nodes(
            run_name,
            GraphNodeQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                node_kind=node_kind,
                operation_id=operation_id,
            ),
        ),
    )


@router.get("/graph/edges/{edge_id}", response_model=GraphEdgeDetailResponse)
def get_graph_edge(
    run_name: str,
    edge_id: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphEdgeDetailResponse:
    return GraphEdgeDetailResponse.from_domain(service.get_graph_edge(run_name, edge_id))


@router.get("/graph/sequences", response_model=GraphSequencePageResponse)
def list_graph_sequences(
    run_name: str,
    target_operation_id: str | None = Query(
        default=None,
        description="Filter by target operation_id.",
    ),
    operation_id: str | None = Query(
        default=None,
        description="Filter to sequences containing this operation_id.",
    ),
    sequence_type: str | None = Query(default=None, description="Filter by sequence type."),
    q: str | None = Query(default=None, description="Search safe sequence fields."),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: sequence_id, target_operation_id, sequence_type, length, score.",
    ),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: target_operation_id, sequence_type.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphSequencePageResponse:
    return GraphSequencePageResponse.from_domain(
        run_name,
        service.list_graph_sequences(
            run_name,
            GraphSequenceQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                target_operation_id=target_operation_id,
                operation_id=operation_id,
                sequence_type=sequence_type,
            ),
        ),
    )


@router.get("/graph/sequences/{sequence_id}", response_model=GraphSequenceResponse)
def get_graph_sequence(
    run_name: str,
    sequence_id: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphSequenceResponse:
    return GraphSequenceResponse.from_domain(
        service.get_graph_sequence(run_name, sequence_id)
    )


@router.get("/graph/facets", response_model=GraphFacetsResponse)
def get_graph_facets(
    run_name: str,
    edge_status: str | None = Query(
        default=None,
        description="Filter by edge status: final, candidate, all.",
    ),
    evidence_source: str | None = Query(default=None, description="Filter by evidence source."),
    from_operation_id: str | None = Query(default=None, description="Filter by producer operation_id."),
    to_operation_id: str | None = Query(default=None, description="Filter by consumer operation_id."),
    node_kind: str | None = Query(default=None, description="Filter by node kind."),
    sequence_type: str | None = Query(default=None, description="Filter by sequence type."),
    q: str | None = Query(default=None, description="Search safe graph explorer fields."),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphFacetsResponse:
    return GraphFacetsResponse.from_domain(
        service.get_graph_facets(
            run_name,
            GraphFacetsQuery(
                edge_status=edge_status,
                evidence_source=evidence_source,
                from_operation_id=from_operation_id,
                to_operation_id=to_operation_id,
                node_kind=node_kind,
                sequence_type=sequence_type,
                q=q,
            ),
        )
    )
