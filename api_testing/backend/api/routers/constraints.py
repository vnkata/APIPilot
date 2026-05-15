from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.constraints import (
    ConstraintExplorerDetailResponse,
    ConstraintExplorerPageResponse,
    ConstraintFacetsResponse,
    ConstraintEntryPageResponse,
    DynamicConstraintsResponse,
    InvariantExplorerDetailResponse,
    InvariantExplorerFacetsResponse,
    InvariantExplorerPageResponse,
    InvariantPageResponse,
    StaticConstraintsResponse,
)
from api_testing.backend.application.querying import (
    ConstraintEntryQuery,
    ConstraintExplorerQuery,
    ConstraintFacetsQuery,
    InvariantExplorerQuery,
    InvariantFacetsQuery,
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


@router.get("/entries", response_model=ConstraintExplorerPageResponse)
def list_constraint_explorer_entries(
    run_name: str,
    source: str | None = Query(
        default=None,
        description="Filter by source. Allowed values: static, dynamic, combined.",
    ),
    operation_id: str | None = Query(
        default=None,
        description="Filter by operation_id.",
    ),
    section: str | None = Query(
        default=None,
        description="Filter by source section, such as request_response or response_properties.",
    ),
    property_path: str | None = Query(
        default=None,
        description="Filter by exact property_path.",
    ),
    property_prefix: str | None = Query(
        default=None,
        description="Filter by property_path prefix.",
    ),
    constraint_kind: str | None = Query(
        default=None,
        description=(
            "Filter by deterministic kind. Allowed values: request_response_relation, "
            "date_format, enum, bounds, required, url, fixed_length, equality, "
            "relation, unknown."
        ),
    ),
    source_type: str | None = Query(
        default=None,
        description="Filter by raw provenance type, such as constraints or request_response.",
    ),
    agreement_status: str | None = Query(
        default=None,
        description=(
            "Filter by correlation status. Allowed values: static_only, dynamic_only, "
            "both_present, combined_only."
        ),
    ),
    assertion_available: bool | None = Query(
        default=None,
        description="Filter by whether a full assertion is available in the detail endpoint.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields across IDs, paths, expressions, provenance, and assertion preview.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, property_path, source, section, constraint_kind, agreement_status.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description=(
            "Allowed values: source, operation_id, section, constraint_kind, "
            "source_type, agreement_status, assertion_available."
        ),
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ConstraintExplorerPageResponse:
    return ConstraintExplorerPageResponse.from_domain(
        run_name,
        service.list_constraint_explorer_entries(
            run_name,
            ConstraintExplorerQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                source=source,
                operation_id=operation_id,
                section=section,
                property_path=property_path,
                property_prefix=property_prefix,
                constraint_kind=constraint_kind,
                source_type=source_type,
                agreement_status=agreement_status,
                assertion_available=assertion_available,
            ),
        ),
    )


@router.get(
    "/entries/{constraint_id}",
    response_model=ConstraintExplorerDetailResponse,
)
def get_constraint_explorer_entry(
    run_name: str,
    constraint_id: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ConstraintExplorerDetailResponse:
    return ConstraintExplorerDetailResponse.from_domain(
        service.get_constraint_explorer_entry(run_name, constraint_id)
    )


@router.get("/facets", response_model=ConstraintFacetsResponse)
def get_constraint_explorer_facets(
    run_name: str,
    source: str | None = Query(
        default=None,
        description="Filter by source. Allowed values: static, dynamic, combined.",
    ),
    operation_id: str | None = Query(
        default=None,
        description="Filter by operation_id.",
    ),
    section: str | None = Query(
        default=None,
        description="Filter by source section, such as request_response or response_properties.",
    ),
    property_path: str | None = Query(
        default=None,
        description="Filter by exact property_path.",
    ),
    property_prefix: str | None = Query(
        default=None,
        description="Filter by property_path prefix.",
    ),
    constraint_kind: str | None = Query(
        default=None,
        description="Filter by deterministic kind.",
    ),
    source_type: str | None = Query(
        default=None,
        description="Filter by raw provenance type.",
    ),
    agreement_status: str | None = Query(
        default=None,
        description="Filter by correlation status.",
    ),
    assertion_available: bool | None = Query(
        default=None,
        description="Filter by whether a full assertion is available.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields before calculating facets.",
    ),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ConstraintFacetsResponse:
    return ConstraintFacetsResponse.from_domain(
        service.get_constraint_explorer_facets(
            run_name,
            ConstraintFacetsQuery(
                source=source,
                operation_id=operation_id,
                section=section,
                property_path=property_path,
                property_prefix=property_prefix,
                constraint_kind=constraint_kind,
                source_type=source_type,
                agreement_status=agreement_status,
                assertion_available=assertion_available,
                q=q,
            ),
        )
    )


@router.get("/dynamic", response_model=DynamicConstraintsResponse)
def get_dynamic_constraints(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> DynamicConstraintsResponse:
    return DynamicConstraintsResponse.from_domain(
        service.get_dynamic_constraints(run_name)
    )


@router.get("/invariants", response_model=InvariantExplorerPageResponse)
def list_invariant_explorer_entries(
    run_name: str,
    operation_id: str | None = Query(default=None, description="Filter by operation_id."),
    invariant_kind: str | None = Query(
        default=None,
        description="Filter by invariant kind. Allowed values: non_null, bounds, enum, equality, size, format, relation, unknown.",
    ),
    invariant_type: str | None = Query(default=None, description="Filter by raw invariant type."),
    oracle_readiness: str | None = Query(
        default=None,
        description="Filter by oracle readiness.",
    ),
    assertion_available: bool | None = Query(
        default=None,
        description="Filter by whether a full postman assertion is available.",
    ),
    correlation_confidence: str | None = Query(
        default=None,
        description="Filter by correlation confidence.",
    ),
    property_path: str | None = Query(default=None, description="Filter by exact property path."),
    property_prefix: str | None = Query(default=None, description="Filter by property path prefix."),
    q: str | None = Query(default=None, description="Search safe invariant fields."),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, primary_property_path, invariant_kind, invariant_type, oracle_readiness, correlation_confidence.",
    ),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, invariant_kind, invariant_type, oracle_readiness, assertion_available, correlation_confidence, primary_property_path.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> InvariantExplorerPageResponse:
    return InvariantExplorerPageResponse.from_domain(
        run_name,
        service.list_invariant_explorer_entries(
            run_name,
            InvariantExplorerQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                operation_id=operation_id,
                invariant_kind=invariant_kind,
                invariant_type=invariant_type,
                oracle_readiness=oracle_readiness,
                assertion_available=assertion_available,
                correlation_confidence=correlation_confidence,
                property_path=property_path,
                property_prefix=property_prefix,
            ),
        ),
    )


@router.get("/invariants/facets", response_model=InvariantExplorerFacetsResponse)
def get_invariant_explorer_facets(
    run_name: str,
    operation_id: str | None = Query(default=None, description="Filter by operation_id."),
    invariant_kind: str | None = Query(default=None, description="Filter by invariant kind."),
    invariant_type: str | None = Query(default=None, description="Filter by raw invariant type."),
    oracle_readiness: str | None = Query(default=None, description="Filter by oracle readiness."),
    assertion_available: bool | None = Query(default=None, description="Filter by assertion availability."),
    correlation_confidence: str | None = Query(default=None, description="Filter by correlation confidence."),
    property_path: str | None = Query(default=None, description="Filter by exact property path."),
    property_prefix: str | None = Query(default=None, description="Filter by property path prefix."),
    q: str | None = Query(default=None, description="Search safe invariant fields before calculating facets."),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> InvariantExplorerFacetsResponse:
    return InvariantExplorerFacetsResponse.from_domain(
        service.get_invariant_explorer_facets(
            run_name,
            InvariantFacetsQuery(
                operation_id=operation_id,
                invariant_kind=invariant_kind,
                invariant_type=invariant_type,
                oracle_readiness=oracle_readiness,
                assertion_available=assertion_available,
                correlation_confidence=correlation_confidence,
                property_path=property_path,
                property_prefix=property_prefix,
                q=q,
            ),
        )
    )


@router.get(
    "/invariants/{invariant_id}",
    response_model=InvariantExplorerDetailResponse,
)
def get_invariant_explorer_entry(
    run_name: str,
    invariant_id: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> InvariantExplorerDetailResponse:
    return InvariantExplorerDetailResponse.from_domain(
        service.get_invariant_explorer_entry(run_name, invariant_id)
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
