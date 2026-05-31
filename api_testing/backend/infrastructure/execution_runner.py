"""In-process execution runner for backend write-flow orchestration."""

from __future__ import annotations

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from api_testing.backend.application.openapi_specs import preview_openapi_operations
from api_testing.backend.application.write_ports import (
    SpecStorageProtocol,
    WriteMetadataRepositoryProtocol,
)
from api_testing.backend.domain.write_models import (
    ExecutionMode,
    ExecutionStatus,
)
from api_testing.backend.settings import BackendSettings


class InProcessExecutionRunner:
    """Runs APIPilot executions in bounded background threads."""

    def __init__(
        self,
        repository: WriteMetadataRepositoryProtocol,
        spec_storage: SpecStorageProtocol,
        settings: BackendSettings,
    ) -> None:
        self.repository = repository
        self.spec_storage = spec_storage
        self.settings = settings
        self._executor = ThreadPoolExecutor(max_workers=settings.max_active_executions)

    def submit(self, execution_id: str) -> None:
        self._executor.submit(self._run, execution_id)

    def _run(self, execution_id: str) -> None:
        try:
            if self.repository.is_cancel_requested(execution_id):
                self._cancel(execution_id)
                return
            execution = self.repository.mark_execution_running(execution_id)
            self.repository.append_execution_event(
                execution_id,
                event_type="running",
                phase="execution",
                message="Execution started",
                status=ExecutionStatus.RUNNING,
            )
            if execution.mode == ExecutionMode.LIVE:
                summary = self._run_live(execution_id)
            else:
                summary = self._run_dry(execution_id)

            if self.repository.is_cancel_requested(execution_id):
                self._cancel(execution_id)
                return

            self.repository.update_execution_status(
                execution_id,
                ExecutionStatus.COMPLETED,
                summary=summary,
            )
            self.repository.append_execution_event(
                execution_id,
                event_type="completed",
                phase="execution",
                message="Execution completed",
                status=ExecutionStatus.COMPLETED,
                metadata=summary,
            )
        except Exception as exc:  # pragma: no cover - exercised through API failure tests
            self.repository.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                error_message=f"{type(exc).__name__}: {exc}",
            )
            self.repository.append_execution_event(
                execution_id,
                event_type="failed",
                phase="execution",
                message="Execution failed",
                status=ExecutionStatus.FAILED,
                metadata={"error": f"{type(exc).__name__}: {exc}"},
            )

    def _run_dry(self, execution_id: str) -> dict[str, Any]:
        execution = self.repository.get_execution(execution_id)
        spec = self.repository.get_spec(execution.spec_id)
        content = self.spec_storage.read_spec(spec.storage_path)
        preview = preview_openapi_operations(content)
        run_dir = self.settings.cache_root / str(execution.run_name)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "baseline_specification.json").write_text(content, encoding="utf-8")
        (run_dir / "specification.json").write_text(
            json.dumps(
                preview.normalized_specification,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "mode": "dry_run",
            "operation_count": len(preview.operations),
            "generated_artifacts": 2,
        }

    def _run_live(self, execution_id: str) -> dict[str, Any]:
        execution = self.repository.get_execution(execution_id)
        spec = self.repository.get_spec(execution.spec_id)
        config = self.repository.get_run_config(execution.run_config_id)
        spec_content = self.spec_storage.read_spec(spec.storage_path)
        spec_path = self.settings.spec_storage_root / f"{execution.execution_id}-live.json"
        spec_path.write_text(spec_content, encoding="utf-8")

        resolved_config = _resolve_secret_refs(config.config)
        llm = _build_llm_config(resolved_config.get("llm") or {})
        embedding = _build_embedding_config(resolved_config.get("embedding") or {})

        from api_testing import APITesting
        from api_testing.config.config_loader import build_embedder, build_llm_from_config
        from api_testing.prompts.factory import PromptFactory

        model = build_llm_from_config(llm)
        embedder = build_embedder({"embedding": embedding})
        prompt_factory = PromptFactory(common_llm=model)
        tester = APITesting(
            base_url=config.base_url,
            base_title=str(execution.run_name),
            spec_path=str(spec_path),
            model=model,
            embedder=embedder,
            constraint_mining=bool(resolved_config.get("constraint_mining", False)),
            prompt_factory=prompt_factory,
        )
        total_testcase, successful = tester.run_tests(
            num_generations=int(resolved_config.get("num_generations") or 1),
            num_test_cases=int(resolved_config.get("num_test_cases") or 1),
            mutation_ratio=float(resolved_config.get("mutation_ratio") or 0.0),
            header_mutation_ratio=float(
                resolved_config.get("header_mutation_ratio") or 0.5
            ),
            async_mode=bool(resolved_config.get("async_mode", False)),
            max_request_workers=resolved_config.get("max_request_workers"),
            async_max_concurrent=int(
                resolved_config.get("async_max_concurrent")
                or self.settings.default_async_max_concurrent
            ),
            headers=resolved_config.get("headers") or {},
        )
        default_run_dir = Path.cwd() / ".cache" / str(execution.run_name)
        configured_run_dir = self.settings.cache_root / str(execution.run_name)
        if default_run_dir.resolve() != configured_run_dir.resolve() and default_run_dir.exists():
            if configured_run_dir.exists():
                shutil.rmtree(configured_run_dir)
            shutil.copytree(default_run_dir, configured_run_dir)
        return {
            "mode": "live",
            "total_test_cases": total_testcase,
            "successful_operations": len(successful),
        }

    def _cancel(self, execution_id: str) -> None:
        self.repository.update_execution_status(
            execution_id,
            ExecutionStatus.CANCELLED,
        )
        self.repository.append_execution_event(
            execution_id,
            event_type="cancelled",
            phase="execution",
            message="Execution cancelled",
            status=ExecutionStatus.CANCELLED,
        )


def _resolve_secret_refs(value: Any) -> Any:
    if isinstance(value, dict) and value.get("type") == "env" and "name" in value:
        return os.getenv(str(value["name"]), "")
    if isinstance(value, dict):
        return {str(key): _resolve_secret_refs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_secret_refs(item) for item in value]
    return value


def _build_llm_config(llm: dict[str, Any]) -> dict[str, Any]:
    provider = str(llm.get("provider") or "openai")
    model = str(llm.get("model") or "gpt-4.1-mini")
    base = {
        "provider": provider,
        "model": model,
        "temperature": float(llm.get("temperature") or 0.0),
        provider: {},
    }
    provider_config = dict(llm)
    provider_config.pop("provider", None)
    provider_config.pop("model", None)
    provider_config.pop("temperature", None)
    base[provider] = provider_config
    return base


def _build_embedding_config(embedding: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": embedding.get("provider") or "huggingface",
        "model": embedding.get("model") or "google/embeddinggemma-300m",
        "use_half": bool(embedding.get("use_half", False)),
        "ollama": {"base_url": embedding.get("base_url") or "http://localhost:11434"},
    }
