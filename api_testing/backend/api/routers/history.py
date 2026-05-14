from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api_testing.backend.api.dependencies import get_artifact_service
from api_testing.backend.api.schemas.history import (
    HarEntryPageResponse,
    HarSessionListResponse,
)
from api_testing.backend.application.services import (
    MAX_PAGE_LIMIT,
    ArtifactQueryService,
)


router = APIRouter(prefix="/api/v1/runs/{run_name}/history", tags=["history"])


@router.get("/sessions", response_model=HarSessionListResponse)
def list_har_sessions(
    run_name: str,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> HarSessionListResponse:
    return HarSessionListResponse.from_domain(
        run_name, service.list_har_sessions(run_name)
    )


@router.get("/sessions/{session_id}/entries", response_model=HarEntryPageResponse)
def list_har_entries(
    run_name: str,
    session_id: str,
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    include_body: bool = False,
    service: ArtifactQueryService = Depends(get_artifact_service),
) -> HarEntryPageResponse:
    return HarEntryPageResponse.from_domain(
        run_name,
        session_id,
        service.list_har_entries(
            run_name,
            session_id=session_id,
            limit=limit,
            offset=offset,
            include_body=include_body,
        ),
    )
