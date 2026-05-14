from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.test_cases import TestCasePageResponse
from api_testing.backend.application.services import (
    MAX_PAGE_LIMIT,
    ArtifactQueryService,
)

__test__ = False


router = APIRouter(prefix="/api/v1/runs/{run_name}", tags=["test-cases"])


@router.get("/test-cases", response_model=TestCasePageResponse)
def list_test_cases(
    run_name: str,
    operation_id: str | None = None,
    status_code: int | None = Query(default=None, ge=100, le=599),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    include_body: bool = False,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> TestCasePageResponse:
    return TestCasePageResponse.from_domain(
        run_name,
        service.list_test_cases(
            run_name,
            operation_id=operation_id,
            status_code=status_code,
            limit=limit,
            offset=offset,
            include_body=include_body,
        ),
    )
