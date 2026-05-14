from __future__ import annotations

from pydantic import JsonValue

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    PaginationMetadata,
)
from api_testing.backend.domain.models import Page, TestCase as DomainTestCase

__test__ = False


class TestCaseResponse(BackendBaseModel):
    test_case_id: str
    operation_id: str
    path: str | None = None
    http_method: str | None = None
    parameters: JsonValue | None = None
    request_body: JsonValue | None = None
    status_code: int | None = None
    response_body: JsonValue | None = None

    @classmethod
    def from_domain(cls, test_case: DomainTestCase) -> "TestCaseResponse":
        return cls(
            test_case_id=test_case.test_case_id,
            operation_id=test_case.operation_id,
            path=test_case.path,
            http_method=test_case.http_method.value if test_case.http_method else None,
            parameters=test_case.parameters,
            request_body=test_case.request_body,
            status_code=test_case.status_code,
            response_body=test_case.response_body,
        )


class TestCasePageResponse(BackendBaseModel):
    run_name: str
    items: list[TestCaseResponse]
    pagination: PaginationMetadata

    @classmethod
    def from_domain(
        cls, run_name: str, page: Page[DomainTestCase]
    ) -> "TestCasePageResponse":
        return cls(
            run_name=run_name,
            items=[TestCaseResponse.from_domain(item) for item in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
        )
