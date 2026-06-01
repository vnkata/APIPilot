"""Subprocess entrypoint for APIPilot live backend executions."""

from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.write_models import ExecutionStatus
from api_testing.backend.infrastructure.execution_runner import (
    _build_embedding_config,
    _build_llm_config,
    _resolve_secret_refs,
    publish_run_artifacts,
)
from api_testing.backend.infrastructure.spec_storage import FileSpecStorage
from api_testing.backend.infrastructure.write_metadata import (
    SQLiteWriteMetadataRepository,
)
from api_testing.backend.settings import BackendSettings


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = BackendSettings(
        cache_root=args.cache_root,
        metadata_db_path=args.metadata_db_path,
        spec_storage_root=args.spec_storage_root,
        allowed_target_base_urls=tuple(args.allowed_target_base_url),
        default_async_max_concurrent=args.default_async_max_concurrent,
    )
    repository = SQLiteWriteMetadataRepository(settings.metadata_db_path)
    spec_storage = FileSpecStorage(settings.spec_storage_root)
    return run_live_execution_worker(
        args.execution_id,
        repository=repository,
        spec_storage=spec_storage,
        settings=settings,
    )


def run_live_execution_worker(
    execution_id: str,
    *,
    repository: SQLiteWriteMetadataRepository,
    spec_storage: FileSpecStorage,
    settings: BackendSettings,
) -> int:
    try:
        summary = _run_live_execution(
            execution_id,
            repository=repository,
            spec_storage=spec_storage,
            settings=settings,
        )
        repository.finalize_active_execution_with_event(
            execution_id,
            ExecutionStatus.COMPLETED,
            event_type="completed",
            phase="execution",
            message="Execution completed",
            summary=summary,
        )
        return 0
    except Exception as exc:  # pragma: no cover - exercised by subprocess monitor
        summary = {
            "reason": "worker_error",
            "error_type": type(exc).__name__,
        }
        repository.finalize_active_execution_with_event(
            execution_id,
            ExecutionStatus.FAILED,
            event_type="failed",
            phase="execution",
            message="Execution worker failed",
            summary=summary,
        )
        return 1


def _run_live_execution(
    execution_id: str,
    *,
    repository: SQLiteWriteMetadataRepository,
    spec_storage: FileSpecStorage,
    settings: BackendSettings,
) -> dict[str, int | str]:
    execution = repository.get_execution(execution_id)
    spec = repository.get_spec(execution.spec_id)
    config = repository.get_run_config(execution.run_config_id)
    _validate_live_execution(
        base_url=config.base_url,
        live_api=config.live_api,
        request_budget=config.request_budget,
        timeout_seconds=config.timeout_seconds,
        allowed_targets=settings.allowed_target_base_urls,
    )

    workspace = settings.cache_root / "_backend" / "workspaces" / execution_id
    workspace.mkdir(parents=True, exist_ok=True)
    spec_path = workspace / "uploaded_spec.json"
    spec_path.write_text(spec_storage.read_spec(spec.storage_path), encoding="utf-8")

    resolved_config = _resolve_secret_refs(config.config)
    llm = _build_llm_config(resolved_config.get("llm") or {})
    embedding = _normalize_embedding_config(
        _build_embedding_config(resolved_config.get("embedding") or {})
    )

    from api_testing import APITesting
    from api_testing.config.config_loader import build_embedder, build_llm_from_config
    from api_testing.events import EventType, get_emitter
    from api_testing.prompts.factory import PromptFactory

    model = build_llm_from_config(llm)
    embedder = build_embedder({"embedding": embedding})
    prompt_factory = PromptFactory(common_llm=model)
    emitter = get_emitter()

    def record_core_event(event) -> None:
        if event.event_type == EventType.OPERATION_UPDATE:
            return
        repository.append_execution_event(
            execution_id,
            event_type=event.event_type.value if event.event_type else "core_event",
            phase=event.phase.value if event.phase else None,
            message=event.message,
            metadata={
                "generation": event.generation,
                "total_generations": event.total_generations,
                "completed_operations": event.completed_operations,
                "total_operations": event.total_operations,
            },
        )

    emitter.subscribe(record_core_event)
    emitter.start()
    try:
        with _pushd(workspace):
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
                    or settings.default_async_max_concurrent
                ),
                headers=resolved_config.get("headers") or {},
            )
    finally:
        emitter._event_queue.join()
        emitter.unsubscribe(record_core_event)
        emitter.stop()

    source_run_dir = workspace / ".cache" / str(execution.run_name)
    target_run_dir = settings.cache_root / str(execution.run_name)
    publish_run_artifacts(source_run_dir, target_run_dir)
    return {
        "mode": "live",
        "total_test_cases": int(total_testcase),
        "successful_operations": len(successful),
        "published_run_name": str(execution.run_name),
    }


def _validate_live_execution(
    *,
    base_url: str,
    live_api: bool,
    request_budget: int | None,
    timeout_seconds: int | None,
    allowed_targets: tuple[str, ...],
) -> None:
    if not live_api:
        raise InvalidArtifactRequest("live worker requires a live run config")
    if not request_budget:
        raise InvalidArtifactRequest("live execution requires request_budget")
    if not timeout_seconds:
        raise InvalidArtifactRequest("live execution requires timeout_seconds")
    if not allowed_targets:
        raise InvalidArtifactRequest("live execution requires a target base URL allowlist")
    parsed = urlparse(base_url)
    for allowed in allowed_targets:
        allowed_parsed = urlparse(allowed)
        if parsed.scheme == allowed_parsed.scheme and parsed.netloc == allowed_parsed.netloc:
            return
    raise InvalidArtifactRequest("base_url is not in the target base URL allowlist")


def _normalize_embedding_config(embedding: dict) -> dict:
    """Make local HuggingFace model paths stable after the worker changes cwd."""
    normalized = dict(embedding)
    if normalized.get("provider") != "huggingface":
        return normalized
    model = normalized.get("model")
    if not isinstance(model, str) or not model.strip():
        return normalized
    model_path = Path(model)
    if model_path.exists():
        normalized["model"] = str(model_path.resolve())
    return normalized


@contextmanager
def _pushd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one APIPilot live execution")
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--metadata-db-path", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--spec-storage-root", required=True, type=Path)
    parser.add_argument(
        "--allowed-target-base-url",
        action="append",
        default=[],
    )
    parser.add_argument("--default-async-max-concurrent", type=int, default=20)
    return parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
