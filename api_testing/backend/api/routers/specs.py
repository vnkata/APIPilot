from __future__ import annotations

from fastapi import APIRouter, Depends, status

from api_testing.backend.api.dependencies import get_write_flow_service
from api_testing.backend.api.schemas.write_flow import (
    SpecCreateRequest,
    SpecListResponse,
    SpecMetadataResponse,
    SpecOperationsResponse,
)
from api_testing.backend.application.write_services import WriteFlowService


router = APIRouter(prefix="/api/v1/specs", tags=["specs"])


@router.post("", response_model=SpecMetadataResponse, status_code=status.HTTP_201_CREATED)
def create_spec(
    request: SpecCreateRequest,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> SpecMetadataResponse:
    spec = service.create_spec(
        filename=request.filename,
        content=request.content,
        title=request.title,
    )
    return SpecMetadataResponse.from_domain(spec)


@router.get("", response_model=SpecListResponse)
def list_specs(
    service: WriteFlowService = Depends(get_write_flow_service),
) -> SpecListResponse:
    return SpecListResponse.from_domain(service.list_specs())


@router.get("/{spec_id}", response_model=SpecMetadataResponse)
def get_spec(
    spec_id: str,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> SpecMetadataResponse:
    return SpecMetadataResponse.from_domain(service.get_spec(spec_id))


@router.get("/{spec_id}/operations", response_model=SpecOperationsResponse)
def preview_spec_operations(
    spec_id: str,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> SpecOperationsResponse:
    return SpecOperationsResponse.from_domain(
        spec_id,
        service.preview_spec_operations(spec_id),
    )

