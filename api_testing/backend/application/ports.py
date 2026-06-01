"""Application ports for artifact persistence."""

from __future__ import annotations

from typing import Protocol

from pydantic import JsonValue

from api_testing.backend.domain.models import (
    ArtifactMetadata,
    ContextualMemoryContextSummary,
    HarSession,
    Run,
)


class ArtifactRepositoryProtocol(Protocol):
    def list_runs(self) -> list[Run]: ...

    def get_run(self, run_name: str) -> Run: ...

    def list_artifacts(self, run_name: str) -> list[ArtifactMetadata]: ...

    def get_artifact(self, run_name: str, artifact_id: str) -> ArtifactMetadata: ...

    def artifact_signature(
        self, run_name: str, artifact_id: str
    ) -> tuple[int, int] | None: ...

    def read_json_artifact(self, run_name: str, artifact_id: str) -> JsonValue: ...

    def read_text_artifact(self, run_name: str, artifact_id: str) -> str: ...

    def read_csv_rows(self, run_name: str, artifact_id: str) -> list[dict[str, str]]: ...

    def read_contextual_memory_summary(
        self, run_name: str, artifact_id: str
    ) -> list[ContextualMemoryContextSummary]: ...

    def list_har_sessions(self, run_name: str) -> list[HarSession]: ...

    def read_har_session(self, run_name: str, session_id: str) -> HarSession: ...
