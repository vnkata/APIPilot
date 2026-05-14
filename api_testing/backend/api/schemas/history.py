from __future__ import annotations

from datetime import datetime

from pydantic import Field, JsonValue

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    PaginationMetadata,
)
from api_testing.backend.domain.models import HarEntry, HarSession, Page


class HarSessionSummaryResponse(BackendBaseModel):
    session_id: str
    entry_count: int = Field(ge=0)
    size_bytes: int = Field(ge=0)
    modified_at: datetime | None = None

    @classmethod
    def from_domain(cls, session: HarSession) -> "HarSessionSummaryResponse":
        return cls(
            session_id=session.session_id,
            entry_count=session.entry_count,
            size_bytes=session.size_bytes,
            modified_at=session.modified_at,
        )


class HarSessionListResponse(BackendBaseModel):
    run_name: str
    sessions: list[HarSessionSummaryResponse]

    @classmethod
    def from_domain(
        cls, run_name: str, sessions: list[HarSession]
    ) -> "HarSessionListResponse":
        return cls(
            run_name=run_name,
            sessions=[
                HarSessionSummaryResponse.from_domain(session)
                for session in sessions
            ],
        )


class HarEntryResponse(BackendBaseModel):
    entry_id: str
    started_at: str | None = None
    duration_ms: float | None = None
    request_method: str | None = None
    request_url: str | None = None
    request_headers: dict[str, str]
    query_params: dict[str, JsonValue]
    request_body: JsonValue | None = None
    response_status: int | None = None
    response_status_text: str | None = None
    response_headers: dict[str, str]
    response_body: JsonValue | None = None

    @classmethod
    def from_domain(cls, entry: HarEntry) -> "HarEntryResponse":
        return cls(
            entry_id=entry.entry_id,
            started_at=entry.started_at,
            duration_ms=entry.duration_ms,
            request_method=entry.request_method,
            request_url=entry.request_url,
            request_headers=entry.request_headers,
            query_params=entry.query_params,
            request_body=entry.request_body,
            response_status=entry.response_status,
            response_status_text=entry.response_status_text,
            response_headers=entry.response_headers,
            response_body=entry.response_body,
        )


class HarEntryPageResponse(BackendBaseModel):
    run_name: str
    session_id: str
    items: list[HarEntryResponse]
    pagination: PaginationMetadata

    @classmethod
    def from_domain(
        cls, run_name: str, session_id: str, page: Page[HarEntry]
    ) -> "HarEntryPageResponse":
        return cls(
            run_name=run_name,
            session_id=session_id,
            items=[HarEntryResponse.from_domain(entry) for entry in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
        )
