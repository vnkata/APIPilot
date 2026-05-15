"""Query-first invariant explorer read service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import re
from typing import TypeVar

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    InvariantExplorerQuery,
    InvariantFacetsQuery,
    QueryOptions,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.explorer_index import (
    RunExplorerIndexService,
)
from api_testing.backend.application.read_services.utils import (
    invariant_record,
    operation_id_from_pptname,
)
from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.backend.domain.models import (
    ConstraintFacetBucket,
    CorrelationConfidence,
    InvariantCorrelationEvidence,
    InvariantExplorerDetail,
    InvariantExplorerEntry,
    InvariantExplorerFacets,
    InvariantExplorerPage,
    InvariantKind,
    OracleReadiness,
)


_ASSERTION_PREVIEW_LIMIT = 160
_TEnum = TypeVar("_TEnum", InvariantKind, OracleReadiness, CorrelationConfidence)
_VARIABLE_PATTERN = re.compile(r"\b(?:return|input)\.[A-Za-z0-9_\[\].{}-]+")


@dataclass(frozen=True, slots=True)
class _InvariantFilters:
    operation_id: str | None
    invariant_kind: InvariantKind | None
    invariant_type: str | None
    oracle_readiness: OracleReadiness | None
    assertion_available: bool | None
    correlation_confidence: CorrelationConfidence | None
    property_path: str | None
    property_prefix: str | None


class InvariantExplorerService:
    """Builds typed invariant explorer rows from invariants.csv."""

    _query_spec = QuerySpec[InvariantExplorerEntry](
        sort_fields={
            "operation_id": lambda item: item.operation_id,
            "primary_property_path": lambda item: item.primary_property_path,
            "invariant_kind": lambda item: item.invariant_kind.value,
            "invariant_type": lambda item: item.invariant_type,
            "oracle_readiness": lambda item: item.oracle_readiness.value,
            "correlation_confidence": lambda item: item.correlation_confidence.value,
        },
        group_fields={
            "operation_id": lambda item: item.operation_id,
            "invariant_kind": lambda item: item.invariant_kind.value,
            "invariant_type": lambda item: item.invariant_type,
            "oracle_readiness": lambda item: item.oracle_readiness.value,
            "assertion_available": lambda item: _bool_key(item.assertion_available),
            "correlation_confidence": lambda item: item.correlation_confidence.value,
            "primary_property_path": lambda item: item.primary_property_path,
        },
        search_fields=[
            lambda item: item.invariant_id,
            lambda item: item.operation_id,
            lambda item: item.pptname,
            lambda item: item.invariant,
            lambda item: item.invariant_type,
            lambda item: item.variables,
            lambda item: item.primary_property_path,
            lambda item: item.invariant_kind.value,
            lambda item: item.oracle_readiness.value,
            lambda item: item.assertion_preview,
        ],
        default_sort=("operation_id", "primary_property_path", "invariant_kind"),
    )

    def __init__(
        self,
        repository: ArtifactRepositoryProtocol,
        index_service: RunExplorerIndexService,
    ) -> None:
        self.repository = repository
        self.index_service = index_service

    def list_entries(
        self,
        run_name: str,
        query: InvariantExplorerQuery,
    ) -> InvariantExplorerPage:
        records = _filter_entries(self.all_entries(run_name), _filters_from_query(query))
        page = query_items(records, spec=self._query_spec, options=query.options)
        return InvariantExplorerPage(
            items=page.items,
            pagination=page.pagination,
            groups=page.groups,
        )

    def all_entries(self, run_name: str) -> list[InvariantExplorerEntry]:
        return [self._entry_from_detail(detail) for detail in self._details(run_name)]

    def get_entry(self, run_name: str, invariant_id: str) -> InvariantExplorerDetail:
        for detail in self._details(run_name):
            if detail.invariant_id == invariant_id:
                return detail
        raise ArtifactNotFound(f"Invariant entry not found: {invariant_id}")

    def get_facets(
        self,
        run_name: str,
        query: InvariantFacetsQuery,
    ) -> InvariantExplorerFacets:
        filters = _filters_from_facets_query(query)
        records = _filter_entries(self.all_entries(run_name), filters)
        records = _search_entries(records, query.q)
        return InvariantExplorerFacets(
            operation_id=_facet(records, lambda item: item.operation_id),
            invariant_kind=_facet(records, lambda item: item.invariant_kind.value),
            invariant_type=_facet(records, lambda item: item.invariant_type),
            oracle_readiness=_facet(records, lambda item: item.oracle_readiness.value),
            assertion_available=_facet(
                records, lambda item: _bool_key(item.assertion_available)
            ),
            correlation_confidence=_facet(
                records, lambda item: item.correlation_confidence.value
            ),
            primary_property_path=_facet(
                records, lambda item: item.primary_property_path
            ),
        )

    def _details(self, run_name: str) -> list[InvariantExplorerDetail]:
        self.repository.get_run(run_name)
        index = self.index_service.get_index(run_name)
        try:
            rows = self.repository.read_csv_rows(run_name, "invariants_csv")
        except ArtifactNotFound:
            return []
        details: list[InvariantExplorerDetail] = []
        for row in rows:
            record = invariant_record(row)
            operation_id = operation_id_from_pptname(record.pptname)
            property_paths = _property_paths(record.variables, record.invariant)
            related_ids, confidence, evidence = _correlate(
                operation_id,
                property_paths,
                index.constraints_by_operation,
                index.constraints_by_operation_property,
            )
            assertion = record.postman_assertion
            readiness = _readiness(
                operation_id=operation_id,
                invariant=record.invariant,
                confidence=confidence,
                related_constraint_ids=related_ids,
            )
            details.append(
                InvariantExplorerDetail(
                    invariant_id=_invariant_id(
                        record.pptname,
                        record.invariant,
                        record.invariant_type,
                        record.variables,
                        assertion,
                    ),
                    operation_id=operation_id,
                    pptname=record.pptname,
                    invariant=record.invariant,
                    invariant_type=record.invariant_type,
                    variables=record.variables,
                    property_paths=property_paths,
                    primary_property_path=property_paths[0] if property_paths else None,
                    invariant_kind=_invariant_kind(
                        record.invariant_type, record.invariant
                    ),
                    oracle_readiness=readiness,
                    assertion_available=bool(assertion),
                    assertion_preview=_preview(assertion),
                    related_constraint_ids=related_ids,
                    correlation_confidence=confidence,
                    correlation_evidence=evidence,
                    postman_assertion=assertion,
                )
            )
        return sorted(
            details,
            key=lambda item: (
                item.operation_id or "",
                item.primary_property_path or "",
                item.invariant_id,
            ),
        )

    @staticmethod
    def _entry_from_detail(detail: InvariantExplorerDetail) -> InvariantExplorerEntry:
        return InvariantExplorerEntry(
            invariant_id=detail.invariant_id,
            operation_id=detail.operation_id,
            pptname=detail.pptname,
            invariant=detail.invariant,
            invariant_type=detail.invariant_type,
            variables=detail.variables,
            property_paths=detail.property_paths,
            primary_property_path=detail.primary_property_path,
            invariant_kind=detail.invariant_kind,
            oracle_readiness=detail.oracle_readiness,
            assertion_available=detail.assertion_available,
            assertion_preview=detail.assertion_preview,
            related_constraint_ids=detail.related_constraint_ids,
            correlation_confidence=detail.correlation_confidence,
            correlation_evidence=detail.correlation_evidence,
        )


def _filters_from_query(query: InvariantExplorerQuery) -> _InvariantFilters:
    return _InvariantFilters(
        operation_id=query.operation_id,
        invariant_kind=_optional_enum(
            InvariantKind, query.invariant_kind, "invariant_kind"
        ),
        invariant_type=query.invariant_type,
        oracle_readiness=_optional_enum(
            OracleReadiness, query.oracle_readiness, "oracle_readiness"
        ),
        assertion_available=query.assertion_available,
        correlation_confidence=_optional_enum(
            CorrelationConfidence,
            query.correlation_confidence,
            "correlation_confidence",
        ),
        property_path=query.property_path,
        property_prefix=query.property_prefix,
    )


def _filters_from_facets_query(query: InvariantFacetsQuery) -> _InvariantFilters:
    return _InvariantFilters(
        operation_id=query.operation_id,
        invariant_kind=_optional_enum(
            InvariantKind, query.invariant_kind, "invariant_kind"
        ),
        invariant_type=query.invariant_type,
        oracle_readiness=_optional_enum(
            OracleReadiness, query.oracle_readiness, "oracle_readiness"
        ),
        assertion_available=query.assertion_available,
        correlation_confidence=_optional_enum(
            CorrelationConfidence,
            query.correlation_confidence,
            "correlation_confidence",
        ),
        property_path=query.property_path,
        property_prefix=query.property_prefix,
    )


def _filter_entries(
    entries: list[InvariantExplorerEntry],
    filters: _InvariantFilters,
) -> list[InvariantExplorerEntry]:
    return [
        entry
        for entry in entries
        if (filters.operation_id is None or entry.operation_id == filters.operation_id)
        and (
            filters.invariant_kind is None
            or entry.invariant_kind == filters.invariant_kind
        )
        and (
            filters.invariant_type is None
            or entry.invariant_type == filters.invariant_type
        )
        and (
            filters.oracle_readiness is None
            or entry.oracle_readiness == filters.oracle_readiness
        )
        and (
            filters.assertion_available is None
            or entry.assertion_available == filters.assertion_available
        )
        and (
            filters.correlation_confidence is None
            or entry.correlation_confidence == filters.correlation_confidence
        )
        and (
            filters.property_path is None
            or filters.property_path in entry.property_paths
        )
        and (
            filters.property_prefix is None
            or any(path.startswith(filters.property_prefix) for path in entry.property_paths)
        )
    ]


def _search_entries(
    entries: list[InvariantExplorerEntry],
    query: str | None,
) -> list[InvariantExplorerEntry]:
    if not query:
        return entries
    options = QueryOptions(q=query, limit=len(entries) or 1, offset=0)
    return query_items(entries, spec=InvariantExplorerService._query_spec, options=options).items


def _property_paths(variables: str | None, invariant: str | None) -> list[str]:
    candidates: list[str] = []
    if variables:
        raw = variables.strip().strip("()")
        candidates.extend(part.strip() for part in raw.split(","))
    if invariant:
        candidates.extend(_VARIABLE_PATTERN.findall(invariant))
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result.append(candidate)
    return result


def _correlate(
    operation_id: str | None,
    property_paths: list[str],
    constraints_by_operation: dict[str, list],
    constraints_by_operation_property: dict[tuple[str, str], list],
) -> tuple[list[str], CorrelationConfidence, list[InvariantCorrelationEvidence]]:
    if operation_id is None:
        return [], CorrelationConfidence.NONE, []

    related_ids: list[str] = []
    evidence: list[InvariantCorrelationEvidence] = []
    for property_path in property_paths:
        constraints = constraints_by_operation_property.get((operation_id, property_path), [])
        for constraint in constraints:
            related_ids.append(constraint.constraint_id)
            evidence.append(
                InvariantCorrelationEvidence(
                    evidence_type="property_path",
                    message="Invariant variable matched a constraint property_path exactly.",
                    property_path=property_path,
                    constraint_id=constraint.constraint_id,
                )
            )
    if related_ids:
        return _unique(related_ids), CorrelationConfidence.EXACT, evidence

    normalized_paths = {_normalize_path(path): path for path in property_paths}
    for constraint in constraints_by_operation.get(operation_id, []):
        normalized_constraint = _normalize_path(constraint.property_path)
        if normalized_constraint in normalized_paths:
            original_path = normalized_paths[normalized_constraint]
            related_ids.append(constraint.constraint_id)
            evidence.append(
                InvariantCorrelationEvidence(
                    evidence_type="normalized_property_path",
                    message="Invariant variable matched a constraint property_path after path normalization.",
                    property_path=original_path,
                    constraint_id=constraint.constraint_id,
                )
            )
    if related_ids:
        return _unique(related_ids), CorrelationConfidence.DERIVED, evidence

    operation_constraints = constraints_by_operation.get(operation_id, [])
    if operation_constraints:
        return (
            [],
            CorrelationConfidence.OPERATION_ONLY,
            [
                InvariantCorrelationEvidence(
                    evidence_type="operation_id",
                    message="Invariant operation_id matched constraints, but no property_path matched.",
                )
            ],
        )
    return [], CorrelationConfidence.NONE, []


def _readiness(
    *,
    operation_id: str | None,
    invariant: str | None,
    confidence: CorrelationConfidence,
    related_constraint_ids: list[str],
) -> OracleReadiness:
    if not operation_id or not invariant:
        return OracleReadiness.NEEDS_HUMAN_REVIEW
    if related_constraint_ids and confidence in {
        CorrelationConfidence.EXACT,
        CorrelationConfidence.DERIVED,
    }:
        return OracleReadiness.SCHEMA_SUPPORTED
    return OracleReadiness.DYNAMIC_CANDIDATE


def _invariant_kind(
    invariant_type: str | None,
    invariant: str | None,
) -> InvariantKind:
    haystack = f"{invariant_type or ''} {invariant or ''}".casefold()
    if any(token in haystack for token in ("nonzero", "!= null", "not null")):
        return InvariantKind.NON_NULL
    if any(token in haystack for token in ("lowerbound", "upperbound", ">=", "<=", ">", "<")):
        return InvariantKind.BOUNDS
    if any(token in haystack for token in ("oneof", " one of ", " in {")):
        return InvariantKind.ENUM
    if any(token in haystack for token in ("int_equal", "intequal", "==")):
        return InvariantKind.EQUALITY
    if "size" in haystack or "length" in haystack:
        return InvariantKind.SIZE
    if "format" in haystack or "date" in haystack:
        return InvariantKind.FORMAT
    if "return." in haystack and "input." in haystack:
        return InvariantKind.RELATION
    return InvariantKind.UNKNOWN


def _invariant_id(*parts: str | None) -> str:
    raw = "\x1f".join(part or "" for part in parts)
    return f"inv_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _preview(value: str | None) -> str | None:
    if value is None:
        return None
    return value if len(value) <= _ASSERTION_PREVIEW_LIMIT else f"{value[:157]}..."


def _normalize_path(value: str) -> str:
    return value.replace("[]", "")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _facet(
    entries: list[InvariantExplorerEntry],
    accessor,
) -> list[ConstraintFacetBucket]:
    counts = Counter(value for entry in entries if (value := accessor(entry)))
    return [
        ConstraintFacetBucket(key=str(key), count=count)
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _optional_enum(enum_type: type[_TEnum], value: str | None, field_name: str) -> _TEnum | None:
    if value is None:
        return None
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise InvalidArtifactRequest(
            f"Unsupported {field_name} '{value}'. Allowed values: {allowed}"
        ) from exc


def _bool_key(value: bool) -> str:
    return "true" if value else "false"
