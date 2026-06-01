from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from api_testing.backend.api.schemas.common import BackendBaseModel, SanitizedBodyResponse
from api_testing.backend.domain.models import (
    ArtifactContent,
    ArtifactKind,
    ArtifactMetadata,
    ArtifactSummaryContent,
    ContextualMemoryContextSummary,
    MediaType,
    RawCsvContent,
    RawJsonContent,
    RawPolicy,
    RawTextContent,
    SanitizedHarEntry,
    SanitizedHarSessionContent,
    SanitizedTestCase,
    SanitizedTestCasesContent,
)


class ArtifactMetadataResponse(BackendBaseModel):
    artifact_id: str
    run_name: str
    kind: ArtifactKind
    relative_path: str
    media_type: MediaType
    size_bytes: int = Field(ge=0)
    modified_at: datetime | None = None
    raw_supported: bool
    summary_supported: bool
    raw_policy: RawPolicy

    @classmethod
    def from_domain(cls, metadata: ArtifactMetadata) -> "ArtifactMetadataResponse":
        return cls(
            artifact_id=metadata.artifact_id,
            run_name=metadata.run_name,
            kind=metadata.kind,
            relative_path=metadata.relative_path,
            media_type=metadata.media_type,
            size_bytes=metadata.size_bytes,
            modified_at=metadata.modified_at,
            raw_supported=metadata.raw_supported,
            summary_supported=metadata.summary_supported,
            raw_policy=metadata.raw_policy,
        )


class ArtifactCatalogResponse(BackendBaseModel):
    run_name: str
    artifacts: list[ArtifactMetadataResponse]

    @classmethod
    def from_domain(
        cls, run_name: str, artifacts: list[ArtifactMetadata]
    ) -> "ArtifactCatalogResponse":
        return cls(
            run_name=run_name,
            artifacts=[
                ArtifactMetadataResponse.from_domain(artifact)
                for artifact in artifacts
            ],
        )


class ArtifactSummaryContentResponse(BackendBaseModel):
    content_kind: Literal["summary"] = "summary"
    kind: ArtifactKind
    top_level_keys: list[str] = []
    object_count: int | None = Field(default=None, ge=0)
    item_count: int | None = Field(default=None, ge=0)
    row_count: int | None = Field(default=None, ge=0)
    columns: list[str] = []
    value_type: str | None = None
    session_id: str | None = None
    entry_count: int | None = Field(default=None, ge=0)
    context_count: int | None = Field(default=None, ge=0)
    contexts: list["ContextualMemoryContextSummaryResponse"] = []

    @classmethod
    def from_domain(
        cls, content: ArtifactSummaryContent
    ) -> "ArtifactSummaryContentResponse":
        return cls(
            kind=content.kind,
            top_level_keys=content.top_level_keys,
            object_count=content.object_count,
            item_count=content.item_count,
            row_count=content.row_count,
            columns=content.columns,
            value_type=content.value_type,
            session_id=content.session_id,
            entry_count=content.entry_count,
            context_count=content.context_count,
            contexts=[
                ContextualMemoryContextSummaryResponse.from_domain(item)
                for item in content.contexts
            ],
        )


class ContextualMemoryContextSummaryResponse(BackendBaseModel):
    context_key: str
    context_kind: str
    payload_kind: str
    item_count: int = Field(ge=0)
    whitelist_count: int = Field(ge=0)
    blacklist_count: int = Field(ge=0)
    updated_at: str | None = None

    @classmethod
    def from_domain(
        cls, content: ContextualMemoryContextSummary
    ) -> "ContextualMemoryContextSummaryResponse":
        return cls(
            context_key=content.context_key,
            context_kind=content.context_kind,
            payload_kind=content.payload_kind,
            item_count=content.item_count,
            whitelist_count=content.whitelist_count,
            blacklist_count=content.blacklist_count,
            updated_at=content.updated_at,
        )


class RawJsonContentResponse(BackendBaseModel):
    content_kind: Literal["raw_json"] = "raw_json"
    value: JsonValue

    @classmethod
    def from_domain(cls, content: RawJsonContent) -> "RawJsonContentResponse":
        return cls(value=content.value)


class RawTextContentResponse(BackendBaseModel):
    content_kind: Literal["raw_text"] = "raw_text"
    text: str

    @classmethod
    def from_domain(cls, content: RawTextContent) -> "RawTextContentResponse":
        return cls(text=content.text)


class RawCsvContentResponse(BackendBaseModel):
    content_kind: Literal["raw_csv"] = "raw_csv"
    rows: list[dict[str, str]]

    @classmethod
    def from_domain(cls, content: RawCsvContent) -> "RawCsvContentResponse":
        return cls(rows=content.rows)


class SanitizedTestCaseResponse(BackendBaseModel):
    test_case_id: str
    operation_id: str
    path: str | None = None
    http_method: str | None = None
    parameters: JsonValue | None = None
    request_body: SanitizedBodyResponse
    status_code: int | None = None
    response_body: SanitizedBodyResponse

    @classmethod
    def from_domain(cls, item: SanitizedTestCase) -> "SanitizedTestCaseResponse":
        return cls(
            test_case_id=item.test_case_id,
            operation_id=item.operation_id,
            path=item.path,
            http_method=item.http_method.value if item.http_method else None,
            parameters=item.parameters,
            request_body=SanitizedBodyResponse.from_domain(item.request_body),
            status_code=item.status_code,
            response_body=SanitizedBodyResponse.from_domain(item.response_body),
        )


class SanitizedHarEntryResponse(BackendBaseModel):
    entry_id: str
    started_at: str | None = None
    duration_ms: float | None = None
    request_method: str | None = None
    request_url: str | None = None
    request_headers: dict[str, str]
    query_params: dict[str, JsonValue]
    request_body: SanitizedBodyResponse
    response_status: int | None = None
    response_status_text: str | None = None
    response_headers: dict[str, str]
    response_body: SanitizedBodyResponse

    @classmethod
    def from_domain(cls, entry: SanitizedHarEntry) -> "SanitizedHarEntryResponse":
        return cls(
            entry_id=entry.entry_id,
            started_at=entry.started_at,
            duration_ms=entry.duration_ms,
            request_method=entry.request_method,
            request_url=entry.request_url,
            request_headers=entry.request_headers,
            query_params=entry.query_params,
            request_body=SanitizedBodyResponse.from_domain(entry.request_body),
            response_status=entry.response_status,
            response_status_text=entry.response_status_text,
            response_headers=entry.response_headers,
            response_body=SanitizedBodyResponse.from_domain(entry.response_body),
        )


class SanitizedTestCasesContentResponse(BackendBaseModel):
    content_kind: Literal["sanitized_test_cases"] = "sanitized_test_cases"
    items: list[SanitizedTestCaseResponse]

    @classmethod
    def from_domain(
        cls, content: SanitizedTestCasesContent
    ) -> "SanitizedTestCasesContentResponse":
        return cls(
            items=[SanitizedTestCaseResponse.from_domain(item) for item in content.items]
        )


class SanitizedHarSessionContentResponse(BackendBaseModel):
    content_kind: Literal["sanitized_har_session"] = "sanitized_har_session"
    session_id: str
    entries: list[SanitizedHarEntryResponse]

    @classmethod
    def from_domain(
        cls, content: SanitizedHarSessionContent
    ) -> "SanitizedHarSessionContentResponse":
        return cls(
            session_id=content.session_id,
            entries=[
                SanitizedHarEntryResponse.from_domain(entry)
                for entry in content.entries
            ],
        )


ArtifactContentValueResponse = Annotated[
    ArtifactSummaryContentResponse
    | RawJsonContentResponse
    | RawTextContentResponse
    | RawCsvContentResponse
    | SanitizedTestCasesContentResponse
    | SanitizedHarSessionContentResponse,
    Field(discriminator="content_kind"),
]


class ArtifactContentResponse(BackendBaseModel):
    run_name: str
    artifact_id: str
    raw: bool
    metadata: ArtifactMetadataResponse
    content: ArtifactContentValueResponse

    @classmethod
    def from_domain(cls, artifact: ArtifactContent) -> "ArtifactContentResponse":
        content = artifact.content
        if isinstance(content, ArtifactSummaryContent):
            response_content = ArtifactSummaryContentResponse.from_domain(content)
        elif isinstance(content, RawJsonContent):
            response_content = RawJsonContentResponse.from_domain(content)
        elif isinstance(content, RawTextContent):
            response_content = RawTextContentResponse.from_domain(content)
        elif isinstance(content, RawCsvContent):
            response_content = RawCsvContentResponse.from_domain(content)
        elif isinstance(content, SanitizedTestCasesContent):
            response_content = SanitizedTestCasesContentResponse.from_domain(content)
        elif isinstance(content, SanitizedHarSessionContent):
            response_content = SanitizedHarSessionContentResponse.from_domain(content)
        else:
            raise TypeError(f"Unsupported artifact content: {type(content)!r}")
        return cls(
            run_name=artifact.run_name,
            artifact_id=artifact.artifact_id,
            raw=artifact.raw,
            metadata=ArtifactMetadataResponse.from_domain(artifact.metadata),
            content=response_content,
        )
