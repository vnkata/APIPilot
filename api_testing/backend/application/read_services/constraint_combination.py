"""Read service for combine_constraint_miners.json artifacts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
import hashlib

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    CombinationFacetsQuery,
    CombinationQuery,
    QueryOptions,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.utils import optional_str
from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.backend.domain.models import (
    CombinationDetail,
    CombinationEntry,
    CombinationEntryPage,
    CombinationFacets,
    CombinationSummary,
    ConstraintFacetBucket,
)
from api_testing.backend.domain.redaction import sanitize_json_value


SOURCE_ARTIFACT = "combine_constraint_miners"
_PREVIEW_LIMIT = 160


@dataclass(frozen=True, slots=True)
class CombinationReadModel:
    entries: list[CombinationEntry]
    details_by_id: dict[str, CombinationDetail]
    summary: CombinationSummary


@dataclass(frozen=True, slots=True)
class _CombinationFilters:
    operation_id: str | None
    property_path: str | None
    property_prefix: str | None
    status: str | None
    verdict: str | None
    resolved: bool | None
    has_counter_example: bool | None
    has_runtime_evaluation: bool | None
    has_validation_cases: bool | None


class ConstraintCombinationService:
    """Builds typed read models for combined static/dynamic constraint evidence."""

    _query_spec = QuerySpec[CombinationEntry](
        sort_fields={
            "operation_id": lambda item: item.operation_id,
            "property_path": lambda item: item.property_path,
            "status": lambda item: item.status,
            "verdict": lambda item: item.verdict,
            "resolved": lambda item: _bool_key(item.resolved),
            "validation_case_count": lambda item: item.validation_case_count,
        },
        group_fields={
            "operation_id": lambda item: item.operation_id,
            "status": lambda item: item.status,
            "verdict": lambda item: item.verdict,
            "resolved": lambda item: _bool_key(item.resolved),
            "has_counter_example": lambda item: _bool_key(item.has_counter_example),
            "has_runtime_evaluation": lambda item: _bool_key(item.has_runtime_evaluation),
            "has_validation_cases": lambda item: _bool_key(item.validation_case_count > 0),
        },
        search_fields=[
            lambda item: item.combination_id,
            lambda item: item.operation_id,
            lambda item: item.property_path,
            lambda item: item.status,
            lambda item: item.verdict,
            lambda item: item.static_constraint,
            lambda item: item.dynamic_constraint,
            lambda item: item.final_constraint,
            lambda item: item.reason_preview,
        ],
        default_sort=("operation_id", "property_path", "status"),
    )

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def get_summary(self, run_name: str) -> CombinationSummary:
        return self._read_model(run_name).summary

    def list_entries(
        self,
        run_name: str,
        query: CombinationQuery,
    ) -> CombinationEntryPage:
        read_model = self._read_model(run_name)
        records = _filter_entries(read_model.entries, _filters_from_query(query))
        page = query_items(records, spec=self._query_spec, options=query.options)
        return CombinationEntryPage(
            items=page.items,
            pagination=page.pagination,
            groups=page.groups,
            malformed_count=read_model.summary.malformed_count,
            warnings=read_model.summary.warnings,
        )

    def get_entry(self, run_name: str, combination_id: str) -> CombinationDetail:
        detail = self._read_model(run_name).details_by_id.get(combination_id)
        if detail is None:
            raise ArtifactNotFound(f"Combination entry not found: {combination_id}")
        return detail

    def get_facets(
        self,
        run_name: str,
        query: CombinationFacetsQuery,
    ) -> CombinationFacets:
        read_model = self._read_model(run_name)
        records = _filter_entries(read_model.entries, _filters_from_facets_query(query))
        records = _search_entries(records, query.q)
        return CombinationFacets(
            status=_facet(records, lambda item: item.status),
            verdict=_facet(records, lambda item: item.verdict),
            resolved=_facet(records, lambda item: _bool_key(item.resolved)),
            operation_id=_facet(records, lambda item: item.operation_id),
            has_counter_example=_facet(
                records, lambda item: _bool_key(item.has_counter_example)
            ),
            has_runtime_evaluation=_facet(
                records, lambda item: _bool_key(item.has_runtime_evaluation)
            ),
            has_validation_cases=_facet(
                records, lambda item: _bool_key(item.validation_case_count > 0)
            ),
            malformed_count=read_model.summary.malformed_count,
            warnings=read_model.summary.warnings,
        )

    def _read_model(self, run_name: str) -> CombinationReadModel:
        self.repository.get_run(run_name)
        payload = self.repository.read_json_artifact(run_name, SOURCE_ARTIFACT)
        return parse_combination_artifact(payload, run_name=run_name)


def parse_combination_artifact(
    payload: JsonValue | None,
    *,
    run_name: str,
    source_artifact: str = SOURCE_ARTIFACT,
) -> CombinationReadModel:
    if not isinstance(payload, dict):
        raise InvalidArtifactRequest(
            "combine_constraint_miners.json must be an object keyed by endpoint"
        )

    malformed_count = 0
    details: list[CombinationDetail] = []
    valid_endpoints: set[str] = set()
    for endpoint_key, raw_properties in payload.items():
        endpoint = str(endpoint_key)
        if not isinstance(raw_properties, dict):
            malformed_count += 1
            continue
        for property_key, raw_record in raw_properties.items():
            if not isinstance(raw_record, dict):
                malformed_count += 1
                continue
            detail = _detail_from_record(
                endpoint,
                str(property_key),
                raw_record,
                source_artifact=source_artifact,
            )
            if detail is None:
                malformed_count += 1
                continue
            details.append(detail)
            valid_endpoints.add(detail.operation_id)

    if not details:
        raise InvalidArtifactRequest(
            "combine_constraint_miners.json contains no valid combination records"
        )

    details = sorted(
        details,
        key=lambda item: (item.operation_id, item.property_path, item.status),
    )
    warnings = _warnings(malformed_count)
    entries = [_entry_from_detail(detail) for detail in details]
    return CombinationReadModel(
        entries=entries,
        details_by_id={detail.combination_id: detail for detail in details},
        summary=CombinationSummary(
            run_name=run_name,
            source_artifact=source_artifact,
            endpoint_count=len(valid_endpoints),
            property_count=len(details),
            resolved_count=sum(1 for detail in details if detail.resolved),
            unresolved_count=sum(1 for detail in details if not detail.resolved),
            malformed_count=malformed_count,
            status_counts=dict(Counter(detail.status for detail in details)),
            verdict_counts=dict(
                Counter(detail.verdict for detail in details if detail.verdict)
            ),
            warnings=warnings,
        ),
    )


def _detail_from_record(
    endpoint_key: str,
    property_key: str,
    record: dict[str, JsonValue],
    *,
    source_artifact: str,
) -> CombinationDetail | None:
    operation_id = optional_str(record.get("endpoint")) or endpoint_key
    property_path = optional_str(record.get("property")) or property_key
    status = optional_str(record.get("status"))
    if not operation_id or not property_path or not status:
        return None

    static_constraint = optional_str(record.get("static_constraint"))
    dynamic_constraint = optional_str(record.get("dynamic_constraint"))
    final_constraint = optional_str(record.get("final_constraint"))
    verdict = optional_str(record.get("verdict"))
    reason = optional_str(record.get("reason"))
    counter_example = _sanitize(record.get("counter_example"))
    runtime_evaluation = _sanitize(record.get("runtime_evaluation"))
    validation_cases = record.get("validation_cases")
    sanitized_validation_cases = (
        [_sanitize(item) for item in validation_cases]
        if isinstance(validation_cases, list)
        else []
    )
    sanitized_record = _sanitize(record)
    if not isinstance(sanitized_record, dict):
        return None
    resolved = record.get("final_constraint") is not None
    detail = CombinationDetail(
        combination_id=_combination_id(
            operation_id,
            property_path,
            status,
            static_constraint,
            dynamic_constraint,
            final_constraint,
        ),
        operation_id=operation_id,
        property_path=property_path,
        status=status,
        verdict=verdict,
        resolved=resolved,
        static_constraint=static_constraint,
        dynamic_constraint=dynamic_constraint,
        final_constraint=final_constraint,
        reason_preview=_preview(reason),
        has_counter_example=record.get("counter_example") is not None,
        has_runtime_evaluation=record.get("runtime_evaluation") is not None,
        validation_case_count=len(validation_cases) if isinstance(validation_cases, list) else 0,
        source_artifact=source_artifact,
        reason=reason,
        counter_example=counter_example,
        runtime_evaluation=runtime_evaluation,
        validation_cases=sanitized_validation_cases,
        raw_record_sanitized=sanitized_record,
    )
    return detail


def _entry_from_detail(detail: CombinationDetail) -> CombinationEntry:
    return CombinationEntry(
        combination_id=detail.combination_id,
        operation_id=detail.operation_id,
        property_path=detail.property_path,
        status=detail.status,
        verdict=detail.verdict,
        resolved=detail.resolved,
        static_constraint=detail.static_constraint,
        dynamic_constraint=detail.dynamic_constraint,
        final_constraint=detail.final_constraint,
        reason_preview=detail.reason_preview,
        has_counter_example=detail.has_counter_example,
        has_runtime_evaluation=detail.has_runtime_evaluation,
        validation_case_count=detail.validation_case_count,
        source_artifact=detail.source_artifact,
    )


def _filters_from_query(query: CombinationQuery) -> _CombinationFilters:
    return _CombinationFilters(
        operation_id=query.operation_id,
        property_path=query.property_path,
        property_prefix=query.property_prefix,
        status=query.status,
        verdict=query.verdict,
        resolved=query.resolved,
        has_counter_example=query.has_counter_example,
        has_runtime_evaluation=query.has_runtime_evaluation,
        has_validation_cases=query.has_validation_cases,
    )


def _filters_from_facets_query(query: CombinationFacetsQuery) -> _CombinationFilters:
    return _CombinationFilters(
        operation_id=query.operation_id,
        property_path=query.property_path,
        property_prefix=query.property_prefix,
        status=query.status,
        verdict=query.verdict,
        resolved=query.resolved,
        has_counter_example=query.has_counter_example,
        has_runtime_evaluation=query.has_runtime_evaluation,
        has_validation_cases=query.has_validation_cases,
    )


def _filter_entries(
    entries: list[CombinationEntry],
    filters: _CombinationFilters,
) -> list[CombinationEntry]:
    return [
        entry
        for entry in entries
        if (filters.operation_id is None or entry.operation_id == filters.operation_id)
        and (
            filters.property_path is None
            or entry.property_path == filters.property_path
        )
        and (
            filters.property_prefix is None
            or entry.property_path.startswith(filters.property_prefix)
        )
        and (filters.status is None or entry.status == filters.status)
        and (filters.verdict is None or entry.verdict == filters.verdict)
        and (filters.resolved is None or entry.resolved == filters.resolved)
        and (
            filters.has_counter_example is None
            or entry.has_counter_example == filters.has_counter_example
        )
        and (
            filters.has_runtime_evaluation is None
            or entry.has_runtime_evaluation == filters.has_runtime_evaluation
        )
        and (
            filters.has_validation_cases is None
            or (entry.validation_case_count > 0) == filters.has_validation_cases
        )
    ]


def _search_entries(
    entries: list[CombinationEntry],
    q: str | None,
) -> list[CombinationEntry]:
    query = q.strip().casefold() if q else ""
    if not query:
        return entries
    return [
        entry
        for entry in entries
        if any(
            query in value.casefold()
            for value in (
                entry.combination_id,
                entry.operation_id,
                entry.property_path,
                entry.status,
                entry.verdict,
                entry.static_constraint,
                entry.dynamic_constraint,
                entry.final_constraint,
                entry.reason_preview,
            )
            if value is not None
        )
    ]


def _facet(
    entries: list[CombinationEntry],
    accessor: Callable[[CombinationEntry], str | None],
) -> list[ConstraintFacetBucket]:
    counts = Counter(value for entry in entries if (value := accessor(entry)))
    return [
        ConstraintFacetBucket(key=str(key), count=count)
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _sanitize(value: JsonValue | None) -> JsonValue | None:
    return sanitize_json_value(value)


def _combination_id(
    operation_id: str,
    property_path: str,
    status: str,
    static_constraint: str | None,
    dynamic_constraint: str | None,
    final_constraint: str | None,
) -> str:
    raw = "\x1f".join(
        [
            operation_id,
            property_path,
            status,
            static_constraint or "",
            dynamic_constraint or "",
            final_constraint or "",
        ]
    )
    return f"cmb_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _preview(value: str | None) -> str | None:
    if value is None:
        return None
    return value if len(value) <= _PREVIEW_LIMIT else f"{value[:_PREVIEW_LIMIT]}..."


def _warnings(malformed_count: int) -> list[str]:
    if malformed_count == 0:
        return []
    noun = "record" if malformed_count == 1 else "records"
    return [f"Skipped {malformed_count} malformed combination {noun}."]


def _bool_key(value: bool) -> str:
    return "true" if value else "false"
