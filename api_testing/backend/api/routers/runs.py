from __future__ import annotations

from fastapi import APIRouter, Depends

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.runs import (
    RunCatalogResponse,
    RunMetadataResponse,
    RunSummaryResponse,
)
from api_testing.backend.application.services import ArtifactQueryService


router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("", response_model=RunCatalogResponse)
def list_runs(
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> RunCatalogResponse:
    return RunCatalogResponse.from_domain(service.list_runs())


@router.get("/{run_name}", response_model=RunMetadataResponse)
def get_run(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> RunMetadataResponse:
    return RunMetadataResponse.from_domain(service.get_run(run_name))


@router.get("/{run_name}/summary", response_model=RunSummaryResponse)
def get_run_summary(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> RunSummaryResponse:
    return RunSummaryResponse.from_domain(service.get_run_summary(run_name))
