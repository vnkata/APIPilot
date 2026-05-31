from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field

from api_testing.backend.api.schemas.common import BackendBaseModel
from api_testing.backend.application.write_services import redact_config
from api_testing.backend.domain.write_models import (
    Execution,
    ExecutionEvent,
    OpenAPIOperation,
    OpenAPIPreview,
    RunConfig,
    RunConfigValidation,
    UploadedSpec,
)


class SpecCreateRequest(BackendBaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=255)


class SpecMetadataResponse(BackendBaseModel):
    spec_id: str
    filename: str
    title: str
    content: None = None
    content_hash: str
    operation_count: int = Field(ge=0)
    created_at: datetime

    @classmethod
    def from_domain(cls, spec: UploadedSpec) -> "SpecMetadataResponse":
        return cls(
            spec_id=spec.spec_id,
            filename=spec.filename,
            title=spec.title,
            content_hash=spec.content_hash,
            operation_count=spec.operation_count,
            created_at=spec.created_at,
        )


class SpecListResponse(BackendBaseModel):
    specs: list[SpecMetadataResponse]

    @classmethod
    def from_domain(cls, specs: list[UploadedSpec]) -> "SpecListResponse":
        return cls(specs=[SpecMetadataResponse.from_domain(spec) for spec in specs])


class SpecOperationResponse(BackendBaseModel):
    operation_id: str
    display_operation_id: str | None = None
    method: str
    path: str
    summary: str | None = None
    has_request_body: bool
    response_statuses: list[str]

    @classmethod
    def from_domain(cls, operation: OpenAPIOperation) -> "SpecOperationResponse":
        return cls(
            operation_id=operation.operation_id,
            display_operation_id=operation.display_operation_id,
            method=operation.method,
            path=operation.path,
            summary=operation.summary,
            has_request_body=operation.has_request_body,
            response_statuses=operation.response_statuses,
        )


class SpecOperationsResponse(BackendBaseModel):
    spec_id: str
    title: str
    version: str | None = None
    operations: list[SpecOperationResponse]

    @classmethod
    def from_domain(
        cls,
        spec_id: str,
        preview: OpenAPIPreview,
    ) -> "SpecOperationsResponse":
        return cls(
            spec_id=spec_id,
            title=preview.title,
            version=preview.version,
            operations=[
                SpecOperationResponse.from_domain(operation)
                for operation in preview.operations
            ],
        )


class SecretRefRequest(BackendBaseModel):
    type: Literal["env"]
    name: str = Field(min_length=1)


class SecretRefResponse(BackendBaseModel):
    type: Literal["env"]
    configured: bool


class LlmConfigRequest(BackendBaseModel):
    model_config = ConfigDict(extra="allow")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    temperature: float | None = None
    api_key: SecretRefRequest | None = None
    base_url: str | None = None
    endpoint: str | None = None
    api_version: str | None = None
    project: str | None = None
    location: str | None = None


class EmbeddingConfigRequest(BackendBaseModel):
    model_config = ConfigDict(extra="allow")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    use_half: bool | None = None
    base_url: str | None = None


class RunConfigRequest(BackendBaseModel):
    name: str = Field(min_length=1, max_length=255)
    spec_id: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    live_api: bool = False
    request_budget: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)
    num_generations: int = Field(default=1, ge=1)
    num_test_cases: int = Field(default=20, ge=1)
    mutation_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    header_mutation_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    async_mode: bool = False
    max_request_workers: int | None = Field(default=None, ge=1)
    async_max_concurrent: int | None = Field(default=None, ge=1)
    constraint_mining: bool = False
    llm: LlmConfigRequest | None = None
    embedding: EmbeddingConfigRequest | None = None
    headers: dict[str, str | SecretRefRequest] = Field(default_factory=dict)


class RunConfigValidationResponse(BackendBaseModel):
    valid: bool
    errors: list[str]

    @classmethod
    def from_domain(
        cls,
        validation: RunConfigValidation,
    ) -> "RunConfigValidationResponse":
        return cls(valid=validation.valid, errors=validation.errors)


class RunConfigResponse(BackendBaseModel):
    run_config_id: str
    name: str
    spec_id: str
    base_url: str
    live_api: bool
    request_budget: int | None = None
    timeout_seconds: int | None = None
    created_at: datetime
    llm: dict[str, Any] | None = None
    embedding: dict[str, Any] | None = None
    headers: dict[str, Any]

    @classmethod
    def from_domain(cls, config: RunConfig) -> "RunConfigResponse":
        redacted = redact_config(config.config)
        return cls(
            run_config_id=config.run_config_id,
            name=config.name,
            spec_id=config.spec_id,
            base_url=config.base_url,
            live_api=config.live_api,
            request_budget=config.request_budget,
            timeout_seconds=config.timeout_seconds,
            created_at=config.created_at,
            llm=redacted.get("llm") if isinstance(redacted, dict) else None,
            embedding=redacted.get("embedding") if isinstance(redacted, dict) else None,
            headers=redacted.get("headers", {}) if isinstance(redacted, dict) else {},
        )


class RunConfigListResponse(BackendBaseModel):
    run_configs: list[RunConfigResponse]

    @classmethod
    def from_domain(cls, configs: list[RunConfig]) -> "RunConfigListResponse":
        return cls(run_configs=[RunConfigResponse.from_domain(config) for config in configs])


class ExecutionCreateRequest(BackendBaseModel):
    spec_id: str = Field(min_length=1)
    run_config_id: str = Field(min_length=1)
    mode: Literal["dry_run", "live"] = "dry_run"


class ExecutionResponse(BackendBaseModel):
    execution_id: str
    spec_id: str
    run_config_id: str
    mode: str
    status: str
    run_name: str | None = None
    summary: dict[str, Any]
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_domain(cls, execution: Execution) -> "ExecutionResponse":
        return cls(
            execution_id=execution.execution_id,
            spec_id=execution.spec_id,
            run_config_id=execution.run_config_id,
            mode=execution.mode.value,
            status=execution.status.value,
            run_name=execution.run_name,
            summary=execution.summary,
            created_at=execution.created_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )


class ExecutionListResponse(BackendBaseModel):
    executions: list[ExecutionResponse]

    @classmethod
    def from_domain(cls, executions: list[Execution]) -> "ExecutionListResponse":
        return cls(
            executions=[ExecutionResponse.from_domain(execution) for execution in executions]
        )


class ExecutionEventResponse(BackendBaseModel):
    event_id: str
    execution_id: str
    sequence: int = Field(ge=1)
    event_type: str
    phase: str | None = None
    message: str | None = None
    status: str | None = None
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_domain(cls, event: ExecutionEvent) -> "ExecutionEventResponse":
        return cls(
            event_id=event.event_id,
            execution_id=event.execution_id,
            sequence=event.sequence,
            event_type=event.event_type,
            phase=event.phase,
            message=event.message,
            status=event.status.value if event.status else None,
            metadata=event.metadata,
            created_at=event.created_at,
        )


class ExecutionEventListResponse(BackendBaseModel):
    events: list[ExecutionEventResponse]

    @classmethod
    def from_domain(cls, events: list[ExecutionEvent]) -> "ExecutionEventListResponse":
        return cls(events=[ExecutionEventResponse.from_domain(event) for event in events])


class ExecutionRunResponse(BackendBaseModel):
    execution_id: str
    run_name: str

    @classmethod
    def from_domain(cls, execution: Execution) -> "ExecutionRunResponse":
        return cls(
            execution_id=execution.execution_id,
            run_name=str(execution.run_name),
        )

