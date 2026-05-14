"""Artifact catalog and content read services."""

from __future__ import annotations

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.read_services.utils import (
    http_method,
    optional_str,
    read_json_list,
    to_int_or_none,
)
from api_testing.backend.domain.models import (
    ArtifactContent,
    ArtifactKind,
    ArtifactMetadata,
    ArtifactSummaryContent,
    RawCsvContent,
    RawJsonContent,
    RawPolicy,
    RawTextContent,
    SanitizedHarSessionContent,
    SanitizedTestCasesContent,
    SanitizedTestCase,
)
from api_testing.backend.domain.redaction import sanitize_body


class ArtifactCatalogService:
    """Reads artifact metadata for a run."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def list_artifacts(self, run_name: str) -> list[ArtifactMetadata]:
        return self.repository.list_artifacts(run_name)


class ArtifactContentService:
    """Builds typed summary or raw content views for artifacts."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def get_artifact_content(
        self,
        run_name: str,
        *,
        artifact_id: str,
        raw: bool,
    ) -> ArtifactContent:
        metadata = self.repository.get_artifact(run_name, artifact_id)
        content = (
            self._raw_artifact_content(run_name, artifact_id, metadata.raw_policy)
            if raw
            else self._artifact_summary(run_name, artifact_id, metadata.kind)
        )
        return ArtifactContent(
            run_name=run_name,
            artifact_id=artifact_id,
            raw=raw,
            metadata=metadata,
            content=content,
        )

    def _artifact_summary(
        self,
        run_name: str,
        artifact_id: str,
        kind: ArtifactKind,
    ) -> ArtifactSummaryContent:
        if artifact_id == "invariants_csv":
            rows = self.repository.read_csv_rows(run_name, artifact_id)
            columns = list(rows[0].keys()) if rows else []
            return ArtifactSummaryContent(
                kind=kind,
                row_count=len(rows),
                columns=columns,
            )
        if kind == ArtifactKind.HAR_SESSION:
            session_id = artifact_id.removeprefix("history_")
            session = self.repository.read_har_session(run_name, session_id)
            return ArtifactSummaryContent(
                kind=kind,
                session_id=session.session_id,
                entry_count=session.entry_count,
            )
        raw = self.repository.read_json_artifact(run_name, artifact_id)
        if isinstance(raw, dict):
            return ArtifactSummaryContent(
                kind=kind,
                top_level_keys=sorted(str(key) for key in raw.keys()),
                object_count=len(raw),
            )
        if isinstance(raw, list):
            return ArtifactSummaryContent(kind=kind, item_count=len(raw))
        return ArtifactSummaryContent(kind=kind, value_type=type(raw).__name__)

    def _raw_artifact_content(
        self,
        run_name: str,
        artifact_id: str,
        raw_policy: RawPolicy,
    ):
        if raw_policy == RawPolicy.SANITIZED_TEST_CASES:
            return SanitizedTestCasesContent(
                items=[
                    self._sanitized_test_case(record)
                    for record in read_json_list(self.repository, run_name, artifact_id)
                    if isinstance(record, dict)
                ]
            )
        if raw_policy == RawPolicy.SANITIZED_HAR_SESSION:
            session_id = artifact_id.removeprefix("history_")
            session = self.repository.read_har_session(run_name, session_id)
            return SanitizedHarSessionContent(
                session_id=session.session_id,
                entries=session.entries,
            )
        if raw_policy == RawPolicy.RAW_CSV:
            return RawCsvContent(rows=self.repository.read_csv_rows(run_name, artifact_id))
        if raw_policy == RawPolicy.RAW_TEXT:
            return RawTextContent(text=self.repository.read_text_artifact(run_name, artifact_id))
        return RawJsonContent(value=self.repository.read_json_artifact(run_name, artifact_id))

    def _sanitized_test_case(self, record: dict[str, JsonValue]) -> SanitizedTestCase:
        return SanitizedTestCase(
            test_case_id=str(record.get("test_case_id", "")),
            operation_id=str(record.get("operation_id", "")),
            path=optional_str(record.get("path")),
            http_method=http_method(record.get("http_method")),
            parameters=record.get("parameters"),
            request_body=sanitize_body(record.get("request_body")),
            status_code=to_int_or_none(record.get("status_code")),
            response_body=sanitize_body(record.get("response_body")),
        )
