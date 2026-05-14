from __future__ import annotations

from pydantic import Field, JsonValue

from api_testing.backend.api.schemas.common import BackendBaseModel
from api_testing.backend.domain.models import OperationDetail, OperationSummary


class OperationSummaryResponse(BackendBaseModel):
    operation_id: str
    display_operation_id: str | None = None
    http_method: str | None = None
    path_template: str | None = None
    parameter_count: int = Field(ge=0)
    response_statuses: list[str]

    @classmethod
    def from_domain(
        cls, operation: OperationSummary
    ) -> "OperationSummaryResponse":
        return cls(
            operation_id=operation.operation_id,
            display_operation_id=operation.display_operation_id,
            http_method=operation.http_method.value if operation.http_method else None,
            path_template=operation.path_template,
            parameter_count=operation.parameter_count,
            response_statuses=operation.response_statuses,
        )


class OperationListResponse(BackendBaseModel):
    run_name: str
    operations: list[OperationSummaryResponse]

    @classmethod
    def from_domain(
        cls, run_name: str, operations: list[OperationSummary]
    ) -> "OperationListResponse":
        return cls(
            run_name=run_name,
            operations=[
                OperationSummaryResponse.from_domain(operation)
                for operation in operations
            ],
        )


class OperationDetailResponse(OperationSummaryResponse):
    parameters: dict[str, JsonValue]
    request_body: JsonValue | None = None
    responses: dict[str, JsonValue]

    @classmethod
    def from_domain(cls, operation: OperationDetail) -> "OperationDetailResponse":
        summary = OperationSummaryResponse.from_domain(operation)
        return cls(
            **summary.model_dump(),
            parameters=operation.parameters,
            request_body=operation.request_body,
            responses=operation.responses,
        )
