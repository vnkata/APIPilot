from __future__ import annotations

from pydantic import Field, JsonValue

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    GroupCountResponse,
    PaginationMetadata,
)
from api_testing.backend.domain.models import (
    ConstraintFacetBucket,
    OperationCountSummary,
    OperationExplorerDetail,
    OperationExplorerEntry,
    OperationExplorerPage,
    OperationFacets,
    OperationGraphSummary,
    OperationDetail,
    OperationSummary,
)


class OperationSummaryResponse(BackendBaseModel):
    operation_id: str
    display_operation_id: str | None = None
    http_method: str | None = None
    path_template: str | None = None
    parameter_count: int = Field(ge=0)
    response_statuses: list[str]

    @classmethod
    def from_domain(
        cls, operation: OperationSummary
    ) -> "OperationSummaryResponse":
        return cls(
            operation_id=operation.operation_id,
            display_operation_id=operation.display_operation_id,
            http_method=operation.http_method.value if operation.http_method else None,
            path_template=operation.path_template,
            parameter_count=operation.parameter_count,
            response_statuses=operation.response_statuses,
        )


class OperationListResponse(BackendBaseModel):
    run_name: str
    operations: list[OperationSummaryResponse]

    @classmethod
    def from_domain(
        cls, run_name: str, operations: list[OperationSummary]
    ) -> "OperationListResponse":
        return cls(
            run_name=run_name,
            operations=[
                OperationSummaryResponse.from_domain(operation)
                for operation in operations
            ],
        )


class OperationDetailResponse(OperationSummaryResponse):
    parameters: dict[str, JsonValue]
    request_body: JsonValue | None = None
    responses: dict[str, JsonValue]

    @classmethod
    def from_domain(cls, operation: OperationDetail) -> "OperationDetailResponse":
        summary = OperationSummaryResponse.from_domain(operation)
        return cls(
            **summary.model_dump(),
            parameters=operation.parameters,
            request_body=operation.request_body,
            responses=operation.responses,
        )


class OperationExplorerEntryResponse(OperationSummaryResponse):
    operation_key: str
    response_status_count: int = Field(ge=0)
    constraint_count: int = Field(ge=0)
    invariant_count: int = Field(ge=0)
    graph_in_degree: int = Field(ge=0)
    graph_out_degree: int = Field(ge=0)
    test_case_count: int = Field(ge=0)
    has_failures: bool

    @classmethod
    def from_domain(
        cls, operation: OperationExplorerEntry
    ) -> "OperationExplorerEntryResponse":
        summary = OperationSummaryResponse.from_domain(operation)
        return cls(
            **summary.model_dump(),
            operation_key=operation.operation_key,
            response_status_count=operation.response_status_count,
            constraint_count=operation.constraint_count,
            invariant_count=operation.invariant_count,
            graph_in_degree=operation.graph_in_degree,
            graph_out_degree=operation.graph_out_degree,
            test_case_count=operation.test_case_count,
            has_failures=operation.has_failures,
        )


class OperationCountSummaryResponse(BackendBaseModel):
    total: int = Field(ge=0)
    by_kind: dict[str, int]

    @classmethod
    def from_domain(
        cls, summary: OperationCountSummary
    ) -> "OperationCountSummaryResponse":
        return cls(total=summary.total, by_kind=summary.by_kind)


class OperationGraphSummaryResponse(BackendBaseModel):
    in_degree: int = Field(ge=0)
    out_degree: int = Field(ge=0)
    incoming_edge_count: int = Field(ge=0)
    outgoing_edge_count: int = Field(ge=0)

    @classmethod
    def from_domain(
        cls, summary: OperationGraphSummary
    ) -> "OperationGraphSummaryResponse":
        return cls(
            in_degree=summary.in_degree,
            out_degree=summary.out_degree,
            incoming_edge_count=summary.incoming_edge_count,
            outgoing_edge_count=summary.outgoing_edge_count,
        )


class OperationExplorerDetailResponse(OperationExplorerEntryResponse):
    parameters: dict[str, JsonValue]
    request_body: JsonValue | None = None
    responses: dict[str, JsonValue]
    constraint_summary: OperationCountSummaryResponse
    invariant_summary: OperationCountSummaryResponse
    graph_summary: OperationGraphSummaryResponse
    report_status_counts: dict[str, int]
    test_case_status_counts: dict[str, int]
    related_constraint_ids: list[str]
    related_invariant_ids: list[str]
    incoming_edge_ids: list[str]
    outgoing_edge_ids: list[str]

    @classmethod
    def from_domain(
        cls, operation: OperationExplorerDetail
    ) -> "OperationExplorerDetailResponse":
        base = OperationExplorerEntryResponse.from_domain(operation).model_dump()
        return cls(
            **base,
            parameters=operation.parameters,
            request_body=operation.request_body,
            responses=operation.responses,
            constraint_summary=OperationCountSummaryResponse.from_domain(
                operation.constraint_summary
            ),
            invariant_summary=OperationCountSummaryResponse.from_domain(
                operation.invariant_summary
            ),
            graph_summary=OperationGraphSummaryResponse.from_domain(
                operation.graph_summary
            ),
            report_status_counts=operation.report_status_counts,
            test_case_status_counts=operation.test_case_status_counts,
            related_constraint_ids=operation.related_constraint_ids,
            related_invariant_ids=operation.related_invariant_ids,
            incoming_edge_ids=operation.incoming_edge_ids,
            outgoing_edge_ids=operation.outgoing_edge_ids,
        )


class OperationExplorerPageResponse(BackendBaseModel):
    run_name: str
    items: list[OperationExplorerEntryResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: OperationExplorerPage,
    ) -> "OperationExplorerPageResponse":
        return cls(
            run_name=run_name,
            items=[
                OperationExplorerEntryResponse.from_domain(item)
                for item in page.items
            ],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class OperationFacetBucketResponse(BackendBaseModel):
    key: str
    count: int = Field(ge=0)

    @classmethod
    def from_domain(cls, bucket: ConstraintFacetBucket) -> "OperationFacetBucketResponse":
        return cls(key=bucket.key, count=bucket.count)


class OperationFacetsResponse(BackendBaseModel):
    http_method: list[OperationFacetBucketResponse]
    response_status: list[OperationFacetBucketResponse]
    has_request_body: list[OperationFacetBucketResponse]
    has_constraints: list[OperationFacetBucketResponse]
    has_invariants: list[OperationFacetBucketResponse]
    has_graph_edges: list[OperationFacetBucketResponse]
    has_failures: list[OperationFacetBucketResponse]

    @classmethod
    def from_domain(cls, facets: OperationFacets) -> "OperationFacetsResponse":
        return cls(
            http_method=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.http_method
            ],
            response_status=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.response_status
            ],
            has_request_body=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_request_body
            ],
            has_constraints=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_constraints
            ],
            has_invariants=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_invariants
            ],
            has_graph_edges=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_graph_edges
            ],
            has_failures=[
                OperationFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_failures
            ],
        )
