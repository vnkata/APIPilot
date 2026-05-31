"""Application services for APIPilot backend write-flow orchestration."""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import urlparse

from api_testing.backend.application.openapi_specs import preview_openapi_operations
from api_testing.backend.application.write_ports import (
    ExecutionRunnerProtocol,
    SpecStorageProtocol,
    WriteMetadataRepositoryProtocol,
)
from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.write_models import (
    Execution,
    ExecutionEvent,
    ExecutionMode,
    ExecutionStatus,
    OpenAPIPreview,
    RunConfig,
    RunConfigCreate,
    RunConfigValidation,
    SpecCreate,
    UploadedSpec,
)


class WriteFlowService:
    """Coordinates uploaded specs, run configs, and execution lifecycle."""

    def __init__(
        self,
        repository: WriteMetadataRepositoryProtocol,
        spec_storage: SpecStorageProtocol,
        runner: ExecutionRunnerProtocol,
        *,
        allowed_target_base_urls: tuple[str, ...],
        max_active_executions: int,
    ) -> None:
        self.repository = repository
        self.spec_storage = spec_storage
        self.runner = runner
        self.allowed_target_base_urls = allowed_target_base_urls
        self.max_active_executions = max_active_executions

    def create_spec(
        self,
        *,
        filename: str,
        content: str,
        title: str | None = None,
    ) -> UploadedSpec:
        preview = preview_openapi_operations(content)
        spec_id = str(uuid.uuid4())
        stored = self.spec_storage.save_spec(filename, content, spec_id=spec_id)
        return self.repository.create_spec(
            SpecCreate(
                filename=filename,
                title=title or preview.title,
                content_hash=stored.content_hash,
                storage_path=stored.storage_path,
                operation_count=len(preview.operations),
            ),
            spec_id=spec_id,
        )

    def list_specs(self) -> list[UploadedSpec]:
        return self.repository.list_specs()

    def get_spec(self, spec_id: str) -> UploadedSpec:
        return self.repository.get_spec(spec_id)

    def preview_spec_operations(self, spec_id: str) -> OpenAPIPreview:
        spec = self.repository.get_spec(spec_id)
        return preview_openapi_operations(self.spec_storage.read_spec(spec.storage_path))

    def validate_run_config(self, payload: dict[str, Any]) -> RunConfigValidation:
        errors: list[str] = []
        spec_id = str(payload.get("spec_id") or "")
        try:
            self.repository.get_spec(spec_id)
        except Exception:
            errors.append(f"Spec not found: {spec_id}")

        base_url = str(payload.get("base_url") or "")
        if not _is_valid_url(base_url):
            errors.append("base_url must be an absolute HTTP(S) URL")

        if payload.get("live_api"):
            errors.extend(self._live_guard_errors(payload))

        llm = payload.get("llm")
        if llm is not None:
            if not isinstance(llm, dict):
                errors.append("llm must be an object")
            else:
                if not llm.get("provider"):
                    errors.append("llm.provider is required")
                if not llm.get("model"):
                    errors.append("llm.model is required")

        embedding = payload.get("embedding")
        if embedding is not None:
            if not isinstance(embedding, dict):
                errors.append("embedding must be an object")
            elif not embedding.get("provider") or not embedding.get("model"):
                errors.append("embedding.provider and embedding.model are required")

        _validate_secret_refs(payload, errors)
        return RunConfigValidation(valid=not errors, errors=errors)

    def create_run_config(self, payload: dict[str, Any]) -> RunConfig:
        validation = self.validate_run_config(payload)
        if not validation.valid:
            raise InvalidArtifactRequest("; ".join(validation.errors))
        return self.repository.create_run_config(
            RunConfigCreate(
                name=str(payload.get("name") or "APIPilot run config"),
                spec_id=str(payload["spec_id"]),
                base_url=str(payload["base_url"]),
                live_api=bool(payload.get("live_api")),
                request_budget=payload.get("request_budget"),
                timeout_seconds=payload.get("timeout_seconds"),
                config=dict(payload),
            )
        )

    def list_run_configs(self) -> list[RunConfig]:
        return self.repository.list_run_configs()

    def get_run_config(self, run_config_id: str) -> RunConfig:
        return self.repository.get_run_config(run_config_id)

    def create_execution(
        self,
        *,
        spec_id: str,
        run_config_id: str,
        mode: ExecutionMode,
    ) -> Execution:
        spec = self.repository.get_spec(spec_id)
        config = self.repository.get_run_config(run_config_id)
        if config.spec_id != spec_id:
            raise InvalidArtifactRequest("run_config_id does not belong to spec_id")
        if self.repository.count_active_executions() >= self.max_active_executions:
            raise InvalidArtifactRequest("active execution limit reached")
        if mode == ExecutionMode.LIVE:
            guard_errors = self._live_guard_errors(config.config)
            if guard_errors:
                raise InvalidArtifactRequest("; ".join(guard_errors))

        execution_id = str(uuid.uuid4())
        run_name = f"{_slug(spec.title)}-{execution_id[:8]}"
        execution = self.repository.create_execution(
            spec_id=spec_id,
            run_config_id=run_config_id,
            mode=mode,
            run_name=run_name,
            execution_id=execution_id,
        )
        self.repository.append_execution_event(
            execution.execution_id,
            event_type="queued",
            phase="execution",
            message="Execution queued",
            status=ExecutionStatus.QUEUED,
        )
        self.runner.submit(execution.execution_id)
        return self.repository.get_execution(execution.execution_id)

    def list_executions(self) -> list[Execution]:
        return self.repository.list_executions()

    def get_execution(self, execution_id: str) -> Execution:
        return self.repository.get_execution(execution_id)

    def cancel_execution(self, execution_id: str) -> Execution:
        execution = self.repository.request_execution_cancel(execution_id)
        self.repository.append_execution_event(
            execution_id,
            event_type="cancel_requested",
            phase="execution",
            message="Cancellation requested",
            status=execution.status,
        )
        return execution

    def list_execution_events(
        self,
        execution_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[ExecutionEvent]:
        return self.repository.list_execution_events(
            execution_id,
            after_sequence=after_sequence,
        )

    def get_execution_run(self, execution_id: str) -> Execution:
        execution = self.repository.get_execution(execution_id)
        if not execution.run_name:
            raise InvalidArtifactRequest("Execution has no published run")
        return execution

    def _live_guard_errors(self, payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        base_url = str(payload.get("base_url") or "")
        if not self.allowed_target_base_urls:
            errors.append("live execution requires a target base URL allowlist")
        elif not _is_allowed_target(base_url, self.allowed_target_base_urls):
            errors.append("base_url is not in the target base URL allowlist")
        if not payload.get("request_budget"):
            errors.append("live execution requires request_budget")
        if not payload.get("timeout_seconds"):
            errors.append("live execution requires timeout_seconds")
        return errors


def redact_config(value: Any) -> Any:
    if _is_secret_ref(value):
        return {"type": "env", "configured": True}
    if isinstance(value, dict):
        return {str(key): redact_config(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_config(item) for item in value]
    return value


def _validate_secret_refs(value: Any, errors: list[str], path: str = "") -> None:
    if _is_secret_ref(value):
        if value.get("type") != "env":
            errors.append(f"{path or 'secret_ref'}.type must be env")
        if not str(value.get("name") or "").strip():
            errors.append(f"{path or 'secret_ref'}.name is required")
        return
    if isinstance(value, dict):
        if "type" in value and value.get("type") == "env":
            _validate_secret_refs(value, errors, path)
            return
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            _validate_secret_refs(item, errors, child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_secret_refs(item, errors, f"{path}[{index}]")


def _is_secret_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value.keys()) >= {"type", "name"}


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_allowed_target(value: str, allowed: tuple[str, ...]) -> bool:
    parsed = urlparse(value)
    for allowed_value in allowed:
        allowed_parsed = urlparse(allowed_value)
        if parsed.scheme == allowed_parsed.scheme and parsed.netloc == allowed_parsed.netloc:
            return True
    return False


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return slug or "apipilot-run"

