from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from api_testing.backend.api.dependencies import get_write_flow_service
from api_testing.backend.api.schemas.write_flow import (
    ExecutionCreateRequest,
    ExecutionEventListResponse,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionRunResponse,
)
from api_testing.backend.application.write_services import WriteFlowService
from api_testing.backend.domain.write_models import ExecutionMode


router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.post("", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
def create_execution(
    request: ExecutionCreateRequest,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> ExecutionResponse:
    execution = service.create_execution(
        spec_id=request.spec_id,
        run_config_id=request.run_config_id,
        mode=ExecutionMode(request.mode),
    )
    return ExecutionResponse.from_domain(execution)


@router.get("", response_model=ExecutionListResponse)
def list_executions(
    service: WriteFlowService = Depends(get_write_flow_service),
) -> ExecutionListResponse:
    return ExecutionListResponse.from_domain(service.list_executions())


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: str,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> ExecutionResponse:
    return ExecutionResponse.from_domain(service.get_execution(execution_id))


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
def cancel_execution(
    execution_id: str,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> ExecutionResponse:
    return ExecutionResponse.from_domain(service.cancel_execution(execution_id))


@router.get("/{execution_id}/events", response_model=ExecutionEventListResponse)
def list_execution_events(
    execution_id: str,
    after_sequence: int = Query(default=0, ge=0),
    service: WriteFlowService = Depends(get_write_flow_service),
) -> ExecutionEventListResponse:
    return ExecutionEventListResponse.from_domain(
        service.list_execution_events(
            execution_id,
            after_sequence=after_sequence,
        )
    )


@router.get("/{execution_id}/run", response_model=ExecutionRunResponse)
def get_execution_run(
    execution_id: str,
    service: WriteFlowService = Depends(get_write_flow_service),
) -> ExecutionRunResponse:
    return ExecutionRunResponse.from_domain(service.get_execution_run(execution_id))

