from __future__ import annotations

from fastapi import APIRouter, Depends, status

from api_testing.backend.api.dependencies import get_write_flow_service
from api_testing.backend.api.schemas.write_flow import (
    RunConfigListResponse,
    RunConfigRequest,
    RunConfigResponse,
    RunConfigValidationResponse,
)
from api_testing.backend.application.write_services import WriteFlowService


router = APIRouter(prefix="/api/v1/run-configs", tags=["run-configs"])


@router.post("/validate", response_model=RunConfigValidationResponse)
def validate_run_config(
    request: RunConfigRequest,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> RunConfigValidationResponse:
    validation = service.validate_run_config(request.model_dump(mode="json"))
    return RunConfigValidationResponse.from_domain(validation)


@router.post("", response_model=RunConfigResponse, status_code=status.HTTP_201_CREATED)
def create_run_config(
    request: RunConfigRequest,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> RunConfigResponse:
    config = service.create_run_config(request.model_dump(mode="json"))
    return RunConfigResponse.from_domain(config)


@router.get("", response_model=RunConfigListResponse)
def list_run_configs(
    service: WriteFlowService = Depends(get_write_flow_service),
) -> RunConfigListResponse:
    return RunConfigListResponse.from_domain(service.list_run_configs())


@router.get("/{run_config_id}", response_model=RunConfigResponse)
def get_run_config(
    run_config_id: str,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> RunConfigResponse:
    return RunConfigResponse.from_domain(service.get_run_config(run_config_id))

