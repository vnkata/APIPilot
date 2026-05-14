from __future__ import annotations

from api_testing.backend.application.services import (
    MAX_PAGE_LIMIT,
    ArtifactQueryService,
)

ArtifactService = ArtifactQueryService

__all__ = ["ArtifactQueryService", "ArtifactService", "MAX_PAGE_LIMIT"]
