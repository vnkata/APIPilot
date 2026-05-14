from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.operations import (
    OperationDetailResponse,
    OperationListResponse,
)
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


@router.get("/operation", response_model=OperationDetailResponse)
def get_operation(
    run_name: str,
    operation_id: str = Query(min_length=1),
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> OperationDetailResponse:
    return OperationDetailResponse.from_domain(
        service.get_operation(run_name, operation_id)
    )
