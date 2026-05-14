from __future__ import annotations

from fastapi import Request

from api_testing.backend.application.services import ArtifactQueryService


def get_artifact_service(request: Request) -> ArtifactQueryService:
    service = getattr(request.app.state, "artifact_service", None)
    if service is None:
        raise RuntimeError("ArtifactQueryService dependency was not initialized")
    return service
