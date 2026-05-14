"""Test case read services."""

from __future__ import annotations

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import TestCaseQuery, page_items
from api_testing.backend.application.read_services.utils import (
    body_for_response,
    http_method,
    optional_str,
    read_json_list,
    to_int,
    to_int_or_none,
)
from api_testing.backend.domain.models import Page, TestCase
from api_testing.backend.domain.redaction import sanitize_body

__test__ = False


class TestCaseQueryService:
    """Builds paged, body-safe test case read models."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def list_test_cases(self, run_name: str, query: TestCaseQuery) -> Page[TestCase]:
        records = self._filtered_records(run_name, query)
        page = page_items(records, query.limit, query.offset)
        return Page(
            items=[
                self._test_case(record, include_body=query.include_body)
                for record in page.items
            ],
            pagination=page.pagination,
        )

    def count_test_cases(self, run_name: str) -> int:
        return len(read_json_list(self.repository, run_name, "test_cases_json"))

    def _filtered_records(
        self,
        run_name: str,
        query: TestCaseQuery,
    ) -> list[dict[str, JsonValue]]:
        records: list[dict[str, JsonValue]] = []
        for record in read_json_list(self.repository, run_name, "test_cases_json"):
            if not isinstance(record, dict):
                continue
            if (
                query.operation_id is not None
                and record.get("operation_id") != query.operation_id
            ):
                continue
            if (
                query.status_code is not None
                and to_int(record.get("status_code")) != query.status_code
            ):
                continue
            records.append(record)
        return records

    def _test_case(
        self,
        record: dict[str, JsonValue],
        *,
        include_body: bool,
    ) -> TestCase:
        return TestCase(
            test_case_id=str(record.get("test_case_id", "")),
            operation_id=str(record.get("operation_id", "")),
            path=optional_str(record.get("path")),
            http_method=http_method(record.get("http_method")),
            parameters=record.get("parameters"),
            request_body=body_for_response(sanitize_body(record.get("request_body")))
            if include_body
            else None,
            status_code=to_int_or_none(record.get("status_code")),
            response_body=body_for_response(sanitize_body(record.get("response_body")))
            if include_body
            else None,
        )
