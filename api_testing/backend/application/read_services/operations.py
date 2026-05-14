"""Operation read models derived from normalized OpenAPI artifacts."""

from __future__ import annotations

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.read_services.utils import (
    http_method,
    optional_str,
)
from api_testing.backend.domain.errors import ArtifactNotFound
from api_testing.backend.domain.models import OperationDetail, OperationSummary


class OperationQueryService:
    """Builds operation summaries and details from specification artifacts."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def list_operations(self, run_name: str) -> list[OperationSummary]:
        operations = self._operations(run_name)
        return sorted(
            [
                self._operation_summary(operation_id, operation)
                for operation_id, operation in operations.items()
            ],
            key=lambda item: item.operation_id,
        )

    def get_operation(self, run_name: str, operation_id: str) -> OperationDetail:
        operations = self._operations(run_name)
        if operation_id not in operations:
            raise ArtifactNotFound(f"Operation not found: {operation_id}")
        operation = operations[operation_id]
        summary = self._operation_summary(operation_id, operation)
        operation_map = operation if isinstance(operation, dict) else {}
        parameters = operation_map.get("parameters", {})
        responses = operation_map.get("responses", {})
        return OperationDetail(
            operation_id=summary.operation_id,
            display_operation_id=summary.display_operation_id,
            http_method=summary.http_method,
            path_template=summary.path_template,
            parameter_count=summary.parameter_count,
            response_statuses=summary.response_statuses,
            parameters=parameters if isinstance(parameters, dict) else {},
            request_body=operation_map.get("request_body"),
            responses=responses if isinstance(responses, dict) else {},
        )

    def _operations(self, run_name: str) -> dict[str, JsonValue]:
        raw = self.repository.read_json_artifact(run_name, "specification")
        spec = raw if isinstance(raw, dict) else {}
        operations = spec.get("operations", {})
        return operations if isinstance(operations, dict) else {}

    def _operation_summary(
        self,
        operation_id: str,
        operation: JsonValue,
    ) -> OperationSummary:
        operation_map = operation if isinstance(operation, dict) else {}
        parameters = operation_map.get("parameters", {})
        responses = operation_map.get("responses", {})
        return OperationSummary(
            operation_id=operation_id,
            display_operation_id=optional_str(operation_map.get("operation_id")),
            http_method=http_method(operation_map.get("http_method")),
            path_template=optional_str(
                operation_map.get("endpoint_path") or operation_map.get("path")
            ),
            parameter_count=len(parameters) if isinstance(parameters, dict) else 0,
            response_statuses=sorted(str(status) for status in responses)
            if isinstance(responses, dict)
            else [],
        )
