"""Report artifact read services."""

from __future__ import annotations

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    QuerySpec,
    ReportEntryQuery,
    query_items,
)
from api_testing.backend.application.read_services.utils import to_int
from api_testing.backend.domain.models import GroupedPage, Reports, StatusReportEntry


class ReportQueryService:
    """Builds aggregate and detailed status-code report read models."""

    _entry_spec = QuerySpec[StatusReportEntry](
        sort_fields={
            "operation_id": lambda item: item.operation_id,
            "status_code": lambda item: item.status_code,
            "count": lambda item: item.count,
        },
        group_fields={
            "operation_id": lambda item: item.operation_id,
            "status_code": lambda item: item.status_code,
        },
        search_fields=[
            lambda item: item.operation_id,
            lambda item: item.status_code,
        ],
        default_sort=("operation_id", "status_code"),
    )

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def get_reports(self, run_name: str) -> Reports:
        raw = self.repository.read_json_artifact(run_name, "reports")
        report_map = raw if isinstance(raw, dict) else {}
        entries: list[StatusReportEntry] = []
        status_counts: dict[str, int] = {}
        for operation_id in sorted(report_map):
            statuses = report_map[operation_id]
            if not isinstance(statuses, dict):
                continue
            for status_code in sorted(statuses, key=str):
                count = to_int(statuses[status_code])
                entries.append(
                    StatusReportEntry(
                        operation_id=str(operation_id),
                        status_code=str(status_code),
                        count=count,
                    )
                )
                status_counts[str(status_code)] = status_counts.get(str(status_code), 0) + count
        return Reports(
            run_name=run_name,
            entries=entries,
            status_counts=dict(sorted(status_counts.items())),
        )

    def list_report_entries(
        self,
        run_name: str,
        query: ReportEntryQuery,
    ) -> GroupedPage[StatusReportEntry]:
        records = [
            entry
            for entry in self.get_reports(run_name).entries
            if (query.operation_id is None or entry.operation_id == query.operation_id)
            and (query.status_code is None or entry.status_code == query.status_code)
        ]
        return query_items(records, spec=self._entry_spec, options=query.options)
