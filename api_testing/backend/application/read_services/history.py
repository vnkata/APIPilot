"""HAR history read services."""

from __future__ import annotations

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import HarEntryQuery, page_items
from api_testing.backend.application.read_services.utils import body_for_response
from api_testing.backend.domain.models import HarEntry, HarSession, Page


class HistoryQueryService:
    """Builds HAR session and entry read models."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def list_har_sessions(self, run_name: str) -> list[HarSession]:
        return self.repository.list_har_sessions(run_name)

    def list_har_entries(self, run_name: str, query: HarEntryQuery) -> Page[HarEntry]:
        session = self.repository.read_har_session(run_name, query.session_id)
        page = page_items(session.entries, query.limit, query.offset)
        return Page(
            items=[
                HarEntry(
                    entry_id=entry.entry_id,
                    started_at=entry.started_at,
                    duration_ms=entry.duration_ms,
                    request_method=entry.request_method,
                    request_url=entry.request_url,
                    request_headers=entry.request_headers,
                    query_params=entry.query_params,
                    request_body=body_for_response(entry.request_body)
                    if query.include_body
                    else None,
                    response_status=entry.response_status,
                    response_status_text=entry.response_status_text,
                    response_headers=entry.response_headers,
                    response_body=body_for_response(entry.response_body)
                    if query.include_body
                    else None,
                )
                for entry in page.items
            ],
            pagination=page.pagination,
        )
