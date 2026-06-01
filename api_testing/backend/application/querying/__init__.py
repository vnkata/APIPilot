"""Typed in-memory query helpers for artifact read models."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.models import GroupCount, GroupedPage, Page, Pagination


MAX_PAGE_LIMIT = 200

T = TypeVar("T")
FieldValue = str | int | float | bool | None
FieldAccessor = Callable[[T], FieldValue]
SearchAccessor = Callable[[T], str | None]


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class QueryOptions:
    q: str | None = None
    limit: int = 50
    offset: int = 0
    sort_by: str | None = None
    sort_order: SortOrder = SortOrder.ASC
    group_by: str | None = None


@dataclass(frozen=True, slots=True)
class QuerySpec(Generic[T]):
    sort_fields: Mapping[str, FieldAccessor[T]]
    group_fields: Mapping[str, FieldAccessor[T]]
    search_fields: Sequence[SearchAccessor[T]]
    default_sort: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConstraintEntryQuery:
    options: QueryOptions
    operation_id: str | None = None
    section: str | None = None


@dataclass(frozen=True, slots=True)
class ConstraintExplorerQuery:
    options: QueryOptions
    source: str | None = None
    operation_id: str | None = None
    section: str | None = None
    property_path: str | None = None
    property_prefix: str | None = None
    constraint_kind: str | None = None
    source_type: str | None = None
    agreement_status: str | None = None
    assertion_available: bool | None = None


@dataclass(frozen=True, slots=True)
class ConstraintFacetsQuery:
    source: str | None = None
    operation_id: str | None = None
    section: str | None = None
    property_path: str | None = None
    property_prefix: str | None = None
    constraint_kind: str | None = None
    source_type: str | None = None
    agreement_status: str | None = None
    assertion_available: bool | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class CombinationQuery:
    options: QueryOptions
    operation_id: str | None = None
    property_path: str | None = None
    property_prefix: str | None = None
    status: str | None = None
    verdict: str | None = None
    resolved: bool | None = None
    has_counter_example: bool | None = None
    has_runtime_evaluation: bool | None = None
    has_validation_cases: bool | None = None


@dataclass(frozen=True, slots=True)
class CombinationFacetsQuery:
    operation_id: str | None = None
    property_path: str | None = None
    property_prefix: str | None = None
    status: str | None = None
    verdict: str | None = None
    resolved: bool | None = None
    has_counter_example: bool | None = None
    has_runtime_evaluation: bool | None = None
    has_validation_cases: bool | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class InvariantQuery:
    options: QueryOptions
    operation_id: str | None = None
    invariant_type: str | None = None


@dataclass(frozen=True, slots=True)
class InvariantExplorerQuery:
    options: QueryOptions
    operation_id: str | None = None
    invariant_kind: str | None = None
    invariant_type: str | None = None
    oracle_readiness: str | None = None
    assertion_available: bool | None = None
    correlation_confidence: str | None = None
    property_path: str | None = None
    property_prefix: str | None = None


@dataclass(frozen=True, slots=True)
class InvariantFacetsQuery:
    operation_id: str | None = None
    invariant_kind: str | None = None
    invariant_type: str | None = None
    oracle_readiness: str | None = None
    assertion_available: bool | None = None
    correlation_confidence: str | None = None
    property_path: str | None = None
    property_prefix: str | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class GraphEdgeQuery:
    options: QueryOptions
    from_node: str | None = None
    to_node: str | None = None


@dataclass(frozen=True, slots=True)
class GraphNodeQuery:
    options: QueryOptions
    node_kind: str | None = None
    operation_id: str | None = None


@dataclass(frozen=True, slots=True)
class GraphEdgeExplorerQuery:
    options: QueryOptions
    from_operation_id: str | None = None
    to_operation_id: str | None = None
    edge_status: str | None = None
    evidence_source: str | None = None


@dataclass(frozen=True, slots=True)
class GraphSequenceQuery:
    options: QueryOptions
    target_operation_id: str | None = None
    operation_id: str | None = None
    sequence_type: str | None = None


@dataclass(frozen=True, slots=True)
class GraphFacetsQuery:
    edge_status: str | None = None
    evidence_source: str | None = None
    from_operation_id: str | None = None
    to_operation_id: str | None = None
    node_kind: str | None = None
    sequence_type: str | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class ReportEntryQuery:
    options: QueryOptions
    operation_id: str | None = None
    status_code: str | None = None


@dataclass(frozen=True, slots=True)
class OperationExplorerQuery:
    options: QueryOptions
    operation_id: str | None = None
    operation_key: str | None = None
    http_method: str | None = None
    response_status: str | None = None
    has_request_body: bool | None = None
    has_constraints: bool | None = None
    has_invariants: bool | None = None
    has_graph_edges: bool | None = None
    has_failures: bool | None = None


@dataclass(frozen=True, slots=True)
class OperationFacetsQuery:
    operation_id: str | None = None
    http_method: str | None = None
    response_status: str | None = None
    has_request_body: bool | None = None
    has_constraints: bool | None = None
    has_invariants: bool | None = None
    has_graph_edges: bool | None = None
    has_failures: bool | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class TestCaseQuery:
    operation_id: str | None
    status_code: int | None
    limit: int
    offset: int
    include_body: bool


@dataclass(frozen=True, slots=True)
class HarEntryQuery:
    session_id: str
    limit: int
    offset: int
    include_body: bool


def query_items(
    records: Iterable[T],
    *,
    spec: QuerySpec[T],
    options: QueryOptions,
) -> GroupedPage[T]:
    """Apply safe search, grouping, sorting, and pagination to in-memory records."""

    _validate_query_spec(spec, options)
    searched = _apply_search(list(records), spec.search_fields, options.q)
    groups = _group_items(searched, spec.group_fields, options.group_by)
    sorted_items = _sort_items(searched, spec, options)
    page_items, pagination = paginate(sorted_items, options.limit, options.offset)
    return GroupedPage(items=page_items, pagination=pagination, groups=groups)


def paginate(records: Sequence[T], limit: int, offset: int) -> tuple[list[T], Pagination]:
    capped_limit = min(limit, MAX_PAGE_LIMIT)
    total = len(records)
    return (
        list(records[offset : offset + capped_limit]),
        Pagination(limit=capped_limit, offset=offset, total=total),
    )


def page_items(records: Sequence[T], limit: int, offset: int) -> Page[T]:
    items, pagination = paginate(records, limit, offset)
    return Page(items=items, pagination=pagination)


def _validate_query_spec(spec: QuerySpec[T], options: QueryOptions) -> None:
    for field in spec.default_sort:
        if field not in spec.sort_fields:
            raise InvalidArtifactRequest(f"Unsupported default sort field: {field}")
    if options.sort_by is not None and options.sort_by not in spec.sort_fields:
        allowed = ", ".join(sorted(spec.sort_fields))
        raise InvalidArtifactRequest(
            f"Unsupported sort_by '{options.sort_by}'. Allowed values: {allowed}"
        )
    if options.group_by is not None and options.group_by not in spec.group_fields:
        allowed = ", ".join(sorted(spec.group_fields))
        raise InvalidArtifactRequest(
            f"Unsupported group_by '{options.group_by}'. Allowed values: {allowed}"
        )


def _apply_search(
    records: list[T],
    search_fields: Sequence[SearchAccessor[T]],
    q: str | None,
) -> list[T]:
    query = q.strip().casefold() if q else ""
    if not query:
        return records
    return [
        record
        for record in records
        if any(_matches_query(accessor(record), query) for accessor in search_fields)
    ]


def _matches_query(value: str | None, query: str) -> bool:
    return value is not None and query in value.casefold()


def _group_items(
    records: list[T],
    group_fields: Mapping[str, FieldAccessor[T]],
    group_by: str | None,
) -> list[GroupCount]:
    if group_by is None:
        return []
    accessor = group_fields[group_by]
    counts = Counter(_group_key(accessor(record)) for record in records)
    return [
        GroupCount(key=key, count=count)
        for key, count in sorted(
            counts.items(),
            key=lambda item: (item[0] is None, "" if item[0] is None else item[0]),
        )
    ]


def _sort_items(
    records: list[T],
    spec: QuerySpec[T],
    options: QueryOptions,
) -> list[T]:
    sort_fields = (options.sort_by,) if options.sort_by else spec.default_sort
    reverse = options.sort_order == SortOrder.DESC
    return sorted(
        records,
        key=lambda record: tuple(
            _sort_component(spec.sort_fields[field](record)) for field in sort_fields
        ),
        reverse=reverse,
    )


def _group_key(value: FieldValue) -> str | None:
    return None if value is None else str(value)


def _sort_component(value: FieldValue) -> tuple[int, float, str]:
    if value is None:
        return (1, 0.0, "")
    if isinstance(value, bool):
        return (0, float(int(value)), str(value).casefold())
    if isinstance(value, int | float):
        return (0, float(value), str(value).casefold())
    return (0, 0.0, value.casefold())
