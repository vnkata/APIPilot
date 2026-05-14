from __future__ import annotations

from fastapi import APIRouter, Depends

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.artifacts import (
    ArtifactCatalogResponse,
    ArtifactContentResponse,
)
from api_testing.backend.application.services import ArtifactQueryService


router = APIRouter(prefix="/api/v1/runs/{run_name}/artifacts", tags=["artifacts"])


@router.get("", response_model=ArtifactCatalogResponse)
def list_artifacts(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ArtifactCatalogResponse:
    return ArtifactCatalogResponse.from_domain(
        run_name, service.list_artifacts(run_name)
    )


@router.get("/{artifact_id}/content", response_model=ArtifactContentResponse)
def get_artifact_content(
    run_name: str,
    artifact_id: str,
    raw: bool = False,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> ArtifactContentResponse:
    return ArtifactContentResponse.from_domain(
        service.get_artifact_content(run_name, artifact_id=artifact_id, raw=raw)
    )
