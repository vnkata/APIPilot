from __future__ import annotations

from pydantic import Field

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    GroupCountResponse,
    PaginationMetadata,
)
from api_testing.backend.domain.models import GroupedPage, Reports, StatusReportEntry


class StatusReportEntryResponse(BackendBaseModel):
    operation_id: str
    status_code: str
    count: int = Field(ge=0)

    @classmethod
    def from_domain(
        cls, entry: StatusReportEntry
    ) -> "StatusReportEntryResponse":
        return cls(
            operation_id=entry.operation_id,
            status_code=entry.status_code,
            count=entry.count,
        )


class ReportsResponse(BackendBaseModel):
    run_name: str
    entries: list[StatusReportEntryResponse]
    status_counts: dict[str, int]

    @classmethod
    def from_domain(cls, reports: Reports) -> "ReportsResponse":
        return cls(
            run_name=reports.run_name,
            entries=[
                StatusReportEntryResponse.from_domain(entry)
                for entry in reports.entries
            ],
            status_counts=reports.status_counts,
        )


class ReportEntryPageResponse(BackendBaseModel):
    run_name: str
    items: list[StatusReportEntryResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: GroupedPage[StatusReportEntry],
    ) -> "ReportEntryPageResponse":
        return cls(
            run_name=run_name,
            items=[StatusReportEntryResponse.from_domain(entry) for entry in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )
