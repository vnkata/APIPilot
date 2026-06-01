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
    COMBINED_CONSTRAINTS = "combined_constraints"
    DYNAMIC_CONSTRAINTS = "dynamic_constraints"
    TEST_CASES = "test_cases"
    INVARIANTS = "invariants"
    USAGE = "usage"
    HAR_SESSION = "har_session"


class MediaType(StrEnum):
    APPLICATION_JSON = "application/json"
    APPLICATION_OCTET_STREAM = "application/octet-stream"
    TEXT_CSV = "text/csv"
    TEXT_PLAIN = "text/plain"


class RawPolicy(StrEnum):
    RAW_JSON = "raw_json"
    RAW_TEXT = "raw_text"
    RAW_CSV = "raw_csv"
    SUMMARY_ONLY = "summary_only"
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


class ConstraintSource(StrEnum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    COMBINED = "combined"


class ConstraintKind(StrEnum):
    REQUEST_RESPONSE_RELATION = "request_response_relation"
    DATE_FORMAT = "date_format"
    ENUM = "enum"
    BOUNDS = "bounds"
    REQUIRED = "required"
    URL = "url"
    FIXED_LENGTH = "fixed_length"
    EQUALITY = "equality"
    RELATION = "relation"
    UNKNOWN = "unknown"


class AgreementStatus(StrEnum):
    STATIC_ONLY = "static_only"
    DYNAMIC_ONLY = "dynamic_only"
    BOTH_PRESENT = "both_present"
    COMBINED_ONLY = "combined_only"


class CombinedSource(StrEnum):
    ARTIFACT = "artifact"
    COMBINE_CONSTRAINT_MINERS = "combine_constraint_miners"
    COMPUTED_FALLBACK = "computed_fallback"


@dataclass(frozen=True, slots=True)
class ConstraintQueryMetadata:
    combined_source: CombinedSource
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class ConstraintExplorerEntry:
    constraint_id: str
    source: ConstraintSource
    operation_id: str
    property_path: str
    expression: str
    section: str | None
    parameter: str | None
    constraint_kind: ConstraintKind
    source_type: str | None
    static_expression: str | None
    dynamic_expression: str | None
    combined_expression: str | None
    has_static: bool
    has_dynamic: bool
    agreement_status: AgreementStatus
    assertion_available: bool
    assertion_preview: str | None


@dataclass(frozen=True, slots=True)
class ConstraintExplorerDetail(ConstraintExplorerEntry):
    assertion: str | None


@dataclass(frozen=True, slots=True)
class ConstraintExplorerPage:
    items: list[ConstraintExplorerEntry]
    pagination: Pagination
    groups: list[GroupCount]
    metadata: ConstraintQueryMetadata


@dataclass(frozen=True, slots=True)
class ConstraintFacetBucket:
    key: str
    count: int


@dataclass(frozen=True, slots=True)
class ConstraintFacets:
    source: list[ConstraintFacetBucket]
    operation_id: list[ConstraintFacetBucket]
    section: list[ConstraintFacetBucket]
    constraint_kind: list[ConstraintFacetBucket]
    source_type: list[ConstraintFacetBucket]
    agreement_status: list[ConstraintFacetBucket]
    assertion_available: list[ConstraintFacetBucket]
    metadata: ConstraintQueryMetadata


@dataclass(frozen=True, slots=True)
class CombinationEntry:
    combination_id: str
    operation_id: str
    property_path: str
    status: str
    verdict: str | None
    resolved: bool
    static_constraint: str | None
    dynamic_constraint: str | None
    final_constraint: str | None
    reason_preview: str | None
    has_counter_example: bool
    has_runtime_evaluation: bool
    validation_case_count: int
    source_artifact: str


@dataclass(frozen=True, slots=True)
class CombinationDetail(CombinationEntry):
    reason: str | None
    counter_example: JsonValue | None
    runtime_evaluation: JsonValue | None
    validation_cases: list[JsonValue]
    raw_record_sanitized: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class CombinationSummary:
    run_name: str
    source_artifact: str
    endpoint_count: int
    property_count: int
    resolved_count: int
    unresolved_count: int
    malformed_count: int
    status_counts: dict[str, int]
    verdict_counts: dict[str, int]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class CombinationEntryPage:
    items: list[CombinationEntry]
    pagination: Pagination
    groups: list[GroupCount]
    malformed_count: int
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class CombinationFacets:
    status: list[ConstraintFacetBucket]
    verdict: list[ConstraintFacetBucket]
    resolved: list[ConstraintFacetBucket]
    operation_id: list[ConstraintFacetBucket]
    has_counter_example: list[ConstraintFacetBucket]
    has_runtime_evaluation: list[ConstraintFacetBucket]
    has_validation_cases: list[ConstraintFacetBucket]
    malformed_count: int
    warnings: list[str]


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


class InvariantKind(StrEnum):
    NON_NULL = "non_null"
    BOUNDS = "bounds"
    ENUM = "enum"
    EQUALITY = "equality"
    SIZE = "size"
    FORMAT = "format"
    RELATION = "relation"
    UNKNOWN = "unknown"


class OracleReadiness(StrEnum):
    DYNAMIC_CANDIDATE = "dynamic_candidate"
    SCHEMA_SUPPORTED = "schema_supported"
    VERIFIED_RUNTIME_ORACLE = "verified_runtime_oracle"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    UNKNOWN = "unknown"


class CorrelationConfidence(StrEnum):
    EXACT = "exact"
    DERIVED = "derived"
    OPERATION_ONLY = "operation_only"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class InvariantCorrelationEvidence:
    evidence_type: str
    message: str
    property_path: str | None = None
    constraint_id: str | None = None


@dataclass(frozen=True, slots=True)
class InvariantExplorerEntry:
    invariant_id: str
    operation_id: str | None
    pptname: str | None
    invariant: str | None
    invariant_type: str | None
    variables: str | None
    property_paths: list[str]
    primary_property_path: str | None
    invariant_kind: InvariantKind
    oracle_readiness: OracleReadiness
    assertion_available: bool
    assertion_preview: str | None
    related_constraint_ids: list[str]
    correlation_confidence: CorrelationConfidence
    correlation_evidence: list[InvariantCorrelationEvidence]


@dataclass(frozen=True, slots=True)
class InvariantExplorerDetail(InvariantExplorerEntry):
    postman_assertion: str | None


@dataclass(frozen=True, slots=True)
class InvariantExplorerPage:
    items: list[InvariantExplorerEntry]
    pagination: Pagination
    groups: list[GroupCount]


@dataclass(frozen=True, slots=True)
class InvariantExplorerFacets:
    operation_id: list[ConstraintFacetBucket]
    invariant_kind: list[ConstraintFacetBucket]
    invariant_type: list[ConstraintFacetBucket]
    oracle_readiness: list[ConstraintFacetBucket]
    assertion_available: list[ConstraintFacetBucket]
    correlation_confidence: list[ConstraintFacetBucket]
    primary_property_path: list[ConstraintFacetBucket]


class GraphNodeKind(StrEnum):
    OPERATION = "operation"
    PROPERTY = "property"
    PARAMETER = "parameter"


class GraphEdgeStatus(StrEnum):
    FINAL = "final"
    CANDIDATE = "candidate"


class GraphEvidenceSource(StrEnum):
    FINAL_GRAPH = "final_graph"
    HEURISTIC_EDGES = "heuristic_edges"
    GPT_EDGES = "gpt_edges"


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    node_kind: GraphNodeKind
    operation_id: str
    label: str
    property_path: str | None
    parameter_name: str | None
    http_method: HttpMethod | None
    path_template: str | None
    in_degree: int
    out_degree: int


@dataclass(frozen=True, slots=True)
class GraphEvidence:
    evidence_id: str
    source: GraphEvidenceSource
    source_artifact_id: str
    value1: str | None
    value2: str | None
    relation_hint: str | None
    from_evidence_node_id: str | None
    to_evidence_node_id: str | None


@dataclass(frozen=True, slots=True)
class GraphExplorerEdge(GraphEdge):
    edge_id: str
    edge_status: GraphEdgeStatus
    from_operation_id: str
    to_operation_id: str
    from_node_id: str
    to_node_id: str
    evidence_count: int
    evidence_sources: list[str]
    evidence_preview: list[str]


@dataclass(frozen=True, slots=True)
class GraphEdgeDetail(GraphExplorerEdge):
    evidence: list[GraphEvidence]


@dataclass(frozen=True, slots=True)
class GraphSequenceParameterSource:
    parameter_name: str
    source_operation_id: str | None
    source_property_path: str | None


@dataclass(frozen=True, slots=True)
class GraphSequence:
    sequence_id: str
    target_operation_id: str | None
    sequence_type: str
    operations: list[str]
    length: int
    score: float | None
    parameter_sources: list[GraphSequenceParameterSource]


@dataclass(frozen=True, slots=True)
class GraphFacets:
    edge_status: list[ConstraintFacetBucket]
    evidence_source: list[ConstraintFacetBucket]
    from_operation_id: list[ConstraintFacetBucket]
    to_operation_id: list[ConstraintFacetBucket]
    node_kind: list[ConstraintFacetBucket]
    sequence_type: list[ConstraintFacetBucket]


@dataclass(frozen=True, slots=True)
class OperationExplorerEntry(OperationSummary):
    operation_key: str
    response_status_count: int
    constraint_count: int
    invariant_count: int
    graph_in_degree: int
    graph_out_degree: int
    test_case_count: int
    has_failures: bool


@dataclass(frozen=True, slots=True)
class OperationCountSummary:
    total: int
    by_kind: dict[str, int]


@dataclass(frozen=True, slots=True)
class OperationGraphSummary:
    in_degree: int
    out_degree: int
    incoming_edge_count: int
    outgoing_edge_count: int


@dataclass(frozen=True, slots=True)
class OperationExplorerDetail(OperationExplorerEntry):
    parameters: dict[str, JsonValue]
    request_body: JsonValue | None
    responses: dict[str, JsonValue]
    constraint_summary: OperationCountSummary
    invariant_summary: OperationCountSummary
    graph_summary: OperationGraphSummary
    report_status_counts: dict[str, int]
    test_case_status_counts: dict[str, int]
    related_constraint_ids: list[str]
    related_invariant_ids: list[str]
    incoming_edge_ids: list[str]
    outgoing_edge_ids: list[str]


@dataclass(frozen=True, slots=True)
class OperationExplorerPage:
    items: list[OperationExplorerEntry]
    pagination: Pagination
    groups: list[GroupCount]


@dataclass(frozen=True, slots=True)
class OperationFacets:
    http_method: list[ConstraintFacetBucket]
    response_status: list[ConstraintFacetBucket]
    has_request_body: list[ConstraintFacetBucket]
    has_constraints: list[ConstraintFacetBucket]
    has_invariants: list[ConstraintFacetBucket]
    has_graph_edges: list[ConstraintFacetBucket]
    has_failures: list[ConstraintFacetBucket]


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
class ContextualMemoryContextSummary:
    context_key: str
    context_kind: str
    payload_kind: str
    item_count: int
    whitelist_count: int
    blacklist_count: int
    updated_at: str | None


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
    context_count: int | None = None
    contexts: list[ContextualMemoryContextSummary] = field(default_factory=list)


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
