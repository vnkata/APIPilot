from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.reports import ReportEntryPageResponse, ReportsResponse
from api_testing.backend.application.querying import (
    QueryOptions,
    ReportEntryQuery,
    SortOrder,
)
from api_testing.backend.application.services import MAX_PAGE_LIMIT, ArtifactQueryService


router = APIRouter(prefix="/api/v1/runs/{run_name}", tags=["reports"])


@router.get("/reports", response_model=ReportsResponse)
def get_reports(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ReportsResponse:
    return ReportsResponse.from_domain(service.get_reports(run_name))


@router.get("/reports/entries", response_model=ReportEntryPageResponse)
def list_report_entries(
    run_name: str,
    operation_id: str | None = Query(
        default=None,
        description="Filter by operation_id.",
    ),
    status_code: str | None = Query(
        default=None,
        description="Filter by HTTP status code.",
    ),
    q: str | None = Query(
        default=None,
        description="Search safe string fields: operation_id, status_code.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, status_code, count.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="Sort direction for sort_by.",
    ),
    group_by: str | None = Query(
        default=None,
        description="Allowed values: operation_id, status_code.",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ReportEntryPageResponse:
    return ReportEntryPageResponse.from_domain(
        run_name,
        service.list_report_entries(
            run_name,
            ReportEntryQuery(
                options=QueryOptions(
                    q=q,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    group_by=group_by,
                ),
                operation_id=operation_id,
                status_code=status_code,
            ),
        ),
    )
