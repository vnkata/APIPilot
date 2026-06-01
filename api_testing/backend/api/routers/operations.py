from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.operations import (
    OperationDetailResponse,
    OperationExplorerDetailResponse,
    OperationExplorerPageResponse,
    OperationFacetsResponse,
    OperationListResponse,
)
from api_testing.backend.application.querying import (
    OperationExplorerQuery,
    OperationFacetsQuery,
    QueryOptions,
    SortOrder,
)
from api_testing.backend.application.services import MAX_PAGE_LIMIT
from api_testing.backend.application.services import ArtifactQueryService


router = APIRouter(prefix="/api/v1/runs/{run_name}", tags=["operations"])


@router.get("/operations", response_model=OperationListResponse)
def list_operations(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> OperationListResponse:
    return OperationListResponse.from_domain(
        run_name, service.list_operations(run_name)
    )


@router.get("/operations/entries", response_model=OperationExplorerPageResponse)
def list_operation_explorer_entries(
    run_name: str,
    operation_id: str | None = Query(default=None, description="Filter by operation_id."),
    operation_key: str | None = Query(default=None, description="Filter by deterministic operation_key."),
    http_method: str | None = Query(default=None, description="Filter by HTTP method."),
    response_status: str | None = Query(default=None, description="Filter by response status."),
    has_request_body: bool | None = Query(default=None, description="Filter by request body availability."),
    has_constraints: bool | None = Query(default=None, description="Filter by mapped constraint availability."),
    has_invariants: bool | None = Query(default=None, description="Filter by raw invariant row availability."),
    has_graph_edges: bool | None = Query(default=None, description="Filter by graph edge availability."),
    has_failures: bool | None = Query(default=None, description="Filter by failure status availability."),
    q: str | None = Query(default=None, description="Search safe operation fields."),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_key, operation_id, http_method, path_template, constraint_count, invariant_count, graph_in_degree, graph_out_degree, test_case_count. invariant_count sorts by raw Daikon invariant row count.",
    ),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: http_method, has_request_body, has_constraints, has_invariants, has_graph_edges, has_failures. has_invariants groups raw invariant row availability.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> OperationExplorerPageResponse:
    return OperationExplorerPageResponse.from_domain(
        run_name,
        service.list_operation_explorer_entries(
            run_name,
            OperationExplorerQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                operation_id=operation_id,
                operation_key=operation_key,
                http_method=http_method,
                response_status=response_status,
                has_request_body=has_request_body,
                has_constraints=has_constraints,
                has_invariants=has_invariants,
                has_graph_edges=has_graph_edges,
                has_failures=has_failures,
            ),
        ),
    )


@router.get("/operations/facets", response_model=OperationFacetsResponse)
def get_operation_explorer_facets(
    run_name: str,
    operation_id: str | None = Query(default=None, description="Filter by operation_id."),
    http_method: str | None = Query(default=None, description="Filter by HTTP method."),
    response_status: str | None = Query(default=None, description="Filter by response status."),
    has_request_body: bool | None = Query(default=None, description="Filter by request body availability."),
    has_constraints: bool | None = Query(default=None, description="Filter by mapped constraint availability."),
    has_invariants: bool | None = Query(default=None, description="Filter by raw invariant row availability."),
    has_graph_edges: bool | None = Query(default=None, description="Filter by graph edge availability."),
    has_failures: bool | None = Query(default=None, description="Filter by failure status availability."),
    q: str | None = Query(default=None, description="Search safe operation fields."),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> OperationFacetsResponse:
    return OperationFacetsResponse.from_domain(
        service.get_operation_explorer_facets(
            run_name,
            OperationFacetsQuery(
                operation_id=operation_id,
                http_method=http_method,
                response_status=response_status,
                has_request_body=has_request_body,
                has_constraints=has_constraints,
                has_invariants=has_invariants,
                has_graph_edges=has_graph_edges,
                has_failures=has_failures,
                q=q,
            ),
        )
    )


@router.get(
    "/operations/entries/{operation_key}",
    response_model=OperationExplorerDetailResponse,
)
def get_operation_explorer_entry(
    run_name: str,
    operation_key: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> OperationExplorerDetailResponse:
    return OperationExplorerDetailResponse.from_domain(
        service.get_operation_explorer_entry(run_name, operation_key)
    )


@router.get("/operation", response_model=OperationDetailResponse)
def get_operation(
    run_name: str,
    operation_id: str = Query(min_length=1),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> OperationDetailResponse:
    return OperationDetailResponse.from_domain(
        service.get_operation(run_name, operation_id)
    )
