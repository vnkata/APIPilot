"""Typed domain models for APIPilot artifact read models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import JsonValue


class ArtifactKind(StrEnum):
    SPECIFICATION = "specification"
    CONFIGURATION = "configuration"
    MEMORY = "memory"
    GRAPH = "graph"
    REPORTS = "reports"
    STATIC_CONSTRAINTS = "static_constraints"
    DYNAMIC_CONSTRAINTS = "dynamic_constraints"
    TEST_CASES = "test_cases"
    INVARIANTS = "invariants"
    USAGE = "usage"
    HAR_SESSION = "har_session"


class MediaType(StrEnum):
    APPLICATION_JSON = "application/json"
    TEXT_CSV = "text/csv"
    TEXT_PLAIN = "text/plain"


class RawPolicy(StrEnum):
    RAW_JSON = "raw_json"
    RAW_TEXT = "raw_text"
    RAW_CSV = "raw_csv"
    SANITIZED_TEST_CASES = "sanitized_test_cases"
    SANITIZED_HAR_SESSION = "sanitized_har_session"


class HttpMethod(StrEnum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"
    HEAD = "head"
    OPTIONS = "options"
    TRACE = "trace"


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int
    offset: int
    total: int


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: list[T]
    pagination: Pagination


@dataclass(frozen=True, slots=True)
class GroupCount:
    key: str | None
    count: int


@dataclass(frozen=True, slots=True)
class GroupedPage(Generic[T]):
    items: list[T]
    pagination: Pagination
    groups: list[GroupCount]


@dataclass(frozen=True, slots=True)
class ArtifactAvailability:
    specification: bool = False
    reports: bool = False
    graph: bool = False
    static_constraints: bool = False
    dynamic_constraints: bool = False
    test_cases: bool = False
    invariants: bool = False
    history: bool = False


@dataclass(frozen=True, slots=True)
class Run:
    run_name: str
    artifact_count: int
    has_history: bool
    size_bytes: int
    modified_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RunSummary:
    run_name: str
    artifact_count: int
    operation_count: int
    test_case_count: int
    har_session_count: int
    static_constraint_count: int
    dynamic_constraint_count: int
    report_status_counts: dict[str, int]
    available_artifacts: ArtifactAvailability


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    artifact_id: str
    run_name: str
    kind: ArtifactKind
    relative_path: str
    media_type: MediaType
    size_bytes: int
    modified_at: datetime | None
    raw_supported: bool
    summary_supported: bool
    raw_policy: RawPolicy


@dataclass(frozen=True, slots=True)
class OperationSummary:
    operation_id: str
    display_operation_id: str | None
    http_method: HttpMethod | None
    path_template: str | None
    parameter_count: int
    response_statuses: list[str]


@dataclass(frozen=True, slots=True)
class OperationDetail(OperationSummary):
    parameters: dict[str, JsonValue]
    request_body: JsonValue | None
    responses: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class StatusReportEntry:
    operation_id: str
    status_code: str
    count: int


@dataclass(frozen=True, slots=True)
class Reports:
    run_name: str
    entries: list[StatusReportEntry]
    status_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class GraphSimilarity:
    value1: str | None = None
    value2: str | None = None
    in_value: str | None = None


@dataclass(frozen=True, slots=True)
class GraphEdge:
    from_node: str
    to_node: str
    similar_parameters: list[GraphSimilarity]


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    run_name: str
    nodes: list[str]
    edges: list[GraphEdge]


@dataclass(frozen=True, slots=True)
class ConstraintEntry:
    operation_id: str
    property_path: str
    expression: str


@dataclass(frozen=True, slots=True)
class ConstraintEntryDetail:
    operation_id: str
    property_path: str
    expression: str
    section: str | None


@dataclass(frozen=True, slots=True)
class ConstraintSection:
    name: str
    constraints: list[ConstraintEntry]


@dataclass(frozen=True, slots=True)
class StaticConstraints:
    run_name: str
    sections: list[ConstraintSection]
    constraint_count: int


@dataclass(frozen=True, slots=True)
class InvariantRecord:
    pptname: str | None = None
    invariant: str | None = None
    invariant_type: str | None = None
    variables: str | None = None
    postman_assertion: str | None = None


@dataclass(frozen=True, slots=True)
class InvariantDetail:
    operation_id: str | None = None
    pptname: str | None = None
    invariant: str | None = None
    invariant_type: str | None = None
    variables: str | None = None
    postman_assertion: str | None = None


@dataclass(frozen=True, slots=True)
class InvariantGroup:
    operation_id: str
    invariants: list[JsonValue]


@dataclass(frozen=True, slots=True)
class DynamicConstraints:
    run_name: str
    constraints: list[ConstraintEntry]
    groups: list[InvariantGroup]
    invariants: list[InvariantRecord]
    constraint_count: int
    invariant_count: int


@dataclass(frozen=True, slots=True)
class SanitizedBody:
    included: bool
    truncated: bool
    content: JsonValue | None
    preview: str | None
    size_bytes: int
    redaction_count: int


@dataclass(frozen=True, slots=True)
class TestCase:
    test_case_id: str
    operation_id: str
    path: str | None
    http_method: HttpMethod | None
    parameters: JsonValue | None
    request_body: JsonValue | None
    status_code: int | None
    response_body: JsonValue | None


@dataclass(frozen=True, slots=True)
class SanitizedTestCase:
    test_case_id: str
    operation_id: str
    path: str | None
    http_method: HttpMethod | None
    parameters: JsonValue | None
    request_body: SanitizedBody
    status_code: int | None
    response_body: SanitizedBody


@dataclass(frozen=True, slots=True)
class HarEntry:
    entry_id: str
    started_at: str | None
    duration_ms: float | None
    request_method: str | None
    request_url: str | None
    request_headers: dict[str, str]
    query_params: dict[str, JsonValue]
    request_body: JsonValue | None
    response_status: int | None
    response_status_text: str | None
    response_headers: dict[str, str]
    response_body: JsonValue | None


@dataclass(frozen=True, slots=True)
class SanitizedHarEntry:
    entry_id: str
    started_at: str | None
    duration_ms: float | None
    request_method: str | None
    request_url: str | None
    request_headers: dict[str, str]
    query_params: dict[str, JsonValue]
    request_body: SanitizedBody
    response_status: int | None
    response_status_text: str | None
    response_headers: dict[str, str]
    response_body: SanitizedBody


@dataclass(frozen=True, slots=True)
class HarSession:
    session_id: str
    entry_count: int
    size_bytes: int
    modified_at: datetime | None = None
    entries: list[SanitizedHarEntry] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ArtifactSummaryContent:
    kind: ArtifactKind
    top_level_keys: list[str] = field(default_factory=list)
    object_count: int | None = None
    item_count: int | None = None
    row_count: int | None = None
    columns: list[str] = field(default_factory=list)
    value_type: str | None = None
    session_id: str | None = None
    entry_count: int | None = None


@dataclass(frozen=True, slots=True)
class RawJsonContent:
    value: JsonValue


@dataclass(frozen=True, slots=True)
class RawTextContent:
    text: str


@dataclass(frozen=True, slots=True)
class RawCsvContent:
    rows: list[dict[str, str]]


@dataclass(frozen=True, slots=True)
class SanitizedTestCasesContent:
    items: list[SanitizedTestCase]


@dataclass(frozen=True, slots=True)
class SanitizedHarSessionContent:
    session_id: str
    entries: list[SanitizedHarEntry]


ArtifactContentValue = (
    ArtifactSummaryContent
    | RawJsonContent
    | RawTextContent
    | RawCsvContent
    | SanitizedTestCasesContent
    | SanitizedHarSessionContent
)


@dataclass(frozen=True, slots=True)
class ArtifactContent:
    run_name: str
    artifact_id: str
    raw: bool
    metadata: ArtifactMetadata
    content: ArtifactContentValue
