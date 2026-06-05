from __future__ import annotations

from fastapi import Request

from api_testing.backend.application.review_services.combination_review import (
    CombinationReviewService,
)
from api_testing.backend.application.research_services.constraint_research import (
    ConstraintResearchService,
)
from api_testing.backend.application.services import ArtifactQueryService
from api_testing.backend.application.write_services import WriteFlowService


def get_artifact_service(request: Request) -> ArtifactQueryService:
    service = getattr(request.app.state, "artifact_service", None)
    if service is None:
        raise RuntimeError("ArtifactQueryService dependency was not initialized")
    return service


def get_write_flow_service(request: Request) -> WriteFlowService:
    service = getattr(request.app.state, "write_flow_service", None)
    if service is None:
        raise RuntimeError("WriteFlowService dependency was not initialized")
    return service


def get_combination_review_service(request: Request) -> CombinationReviewService:
    service = getattr(request.app.state, "combination_review_service", None)
    if service is None:
        raise RuntimeError("CombinationReviewService dependency was not initialized")
    return service


def get_constraint_research_service(request: Request) -> ConstraintResearchService:
    service = getattr(request.app.state, "constraint_research_service", None)
    if service is None:
        raise RuntimeError("ConstraintResearchService dependency was not initialized")
    return service
