from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.dependency_graph import (
    DependencyGraphResponse,
    GraphEdgePageResponse,
)
from api_testing.backend.application.querying import (
    GraphEdgeQuery,
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
    q: str | None = Query(
        default=None,
        description="Search safe string fields: from_node, to_node.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: from_node, to_node.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: from_node, to_node.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> GraphEdgePageResponse:
    return GraphEdgePageResponse.from_domain(
        run_name,
        service.list_graph_edges(
            run_name,
            GraphEdgeQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                from_node=from_node,
                to_node=to_node,
            ),
        ),
    )
