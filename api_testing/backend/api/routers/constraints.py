from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.constraints import (
    ConstraintEntryPageResponse,
    DynamicConstraintsResponse,
    InvariantPageResponse,
    StaticConstraintsResponse,
)
from api_testing.backend.application.querying import (
    ConstraintEntryQuery,
    InvariantQuery,
    QueryOptions,
    SortOrder,
)
from api_testing.backend.application.services import MAX_PAGE_LIMIT, ArtifactQueryService


router = APIRouter(prefix="/api/v1/runs/{run_name}/constraints", tags=["constraints"])


@router.get("/static", response_model=StaticConstraintsResponse)
def get_static_constraints(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> StaticConstraintsResponse:
    return StaticConstraintsResponse.from_domain(
        service.get_static_constraints(run_name)
    )


@router.get("/static/entries", response_model=ConstraintEntryPageResponse)
def list_static_constraint_entries(
    run_name: str,
    operation_id: str | None = Query(
        default=None,
        description="Filter by operation_id.",
    ),
    section: str | None = Query(
        default=None,
        description="Filter by section. Known static sections: common, request_response, response_properties.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields: operation_id, property_path, expression, section.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, property_path, section.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, section.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ConstraintEntryPageResponse:
    return ConstraintEntryPageResponse.from_domain(
        run_name,
        service.list_static_constraint_entries(
            run_name,
            ConstraintEntryQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                operation_id=operation_id,
                section=section,
            ),
        ),
    )


@router.get("/dynamic", response_model=DynamicConstraintsResponse)
def get_dynamic_constraints(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> DynamicConstraintsResponse:
    return DynamicConstraintsResponse.from_domain(
        service.get_dynamic_constraints(run_name)
    )


@router.get("/dynamic/entries", response_model=ConstraintEntryPageResponse)
def list_dynamic_constraint_entries(
    run_name: str,
    operation_id: str | None = Query(
        default=None,
        description="Filter by operation_id.",
    ),
    section: str | None = Query(
        default=None,
        description="Filter by section when the dynamic artifact provides one.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields: operation_id, property_path, expression, section.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, property_path, section.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, section.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ConstraintEntryPageResponse:
    return ConstraintEntryPageResponse.from_domain(
        run_name,
        service.list_dynamic_constraint_entries(
            run_name,
            ConstraintEntryQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                operation_id=operation_id,
                section=section,
            ),
        ),
    )


@router.get("/dynamic/invariants", response_model=InvariantPageResponse)
def list_dynamic_invariants(
    run_name: str,
    operation_id: str | None = Query(
        default=None,
        description="Filter by derived operation_id.",
    ),
    invariant_type: str | None = Query(
        default=None,
        description="Filter by invariant_type.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields: operation_id, pptname, invariant, invariant_type, variables, postman_assertion.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, invariant_type, pptname, invariant.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, invariant_type.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> InvariantPageResponse:
    return InvariantPageResponse.from_domain(
        run_name,
        service.list_invariants(
            run_name,
            InvariantQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                operation_id=operation_id,
                invariant_type=invariant_type,
            ),
        ),
    )
