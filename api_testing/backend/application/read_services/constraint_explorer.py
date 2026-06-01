"""Unified property-level constraint explorer read service."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import re
from typing import TypeVar

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    ConstraintExplorerQuery,
    ConstraintFacetsQuery,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.utils import (
    operation_id_from_pptname,
    optional_str,
)
from api_testing.backend.application.read_services.constraint_combination import (
    SOURCE_ARTIFACT as COMBINATION_SOURCE_ARTIFACT,
    parse_combination_artifact,
)
from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.backend.domain.models import (
    AgreementStatus,
    CombinedSource,
    CombinationEntry,
    ConstraintExplorerDetail,
    ConstraintExplorerEntry,
    ConstraintExplorerPage,
    ConstraintFacetBucket,
    ConstraintFacets,
    ConstraintKind,
    ConstraintQueryMetadata,
    ConstraintSource,
)


_FALLBACK_WARNING = (
    "constraint_miner.json is missing; combined constraints were computed from static "
    "and dynamic artifacts."
)
_COMBINATION_FALLBACK_WARNING = (
    "combine_constraint_miners.json could not be used; falling back to legacy "
    "combined constraint artifacts."
)
_ASSERTION_PREVIEW_LIMIT = 160
_PARTICIPATING_ARTIFACTS = (
    "combine_constraint_miners",
    "constraint_miner",
    "static_constraint_miner",
    "static_constraint_miner_request_response",
    "static_constraint_miner_response_properties",
    "dynamic_constraint_miner",
    "invariants_csv",
)

_TEnum = TypeVar("_TEnum", ConstraintSource, ConstraintKind, AgreementStatus)
_FileSignature = tuple[int, int]
_CacheKey = tuple[str, tuple[tuple[str, _FileSignature | None], ...]]
_ConstraintKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class _NormalizedConstraint:
    source: ConstraintSource
    operation_id: str
    property_path: str
    expression: str
    section: str | None
    parameter: str | None
    source_type: str | None


@dataclass(frozen=True, slots=True)
class _ConstraintFilters:
    source: ConstraintSource | None
    operation_id: str | None
    section: str | None
    property_path: str | None
    property_prefix: str | None
    constraint_kind: ConstraintKind | None
    source_type: str | None
    agreement_status: AgreementStatus | None
    assertion_available: bool | None


@dataclass(frozen=True, slots=True)
class _ReadModel:
    entries: list[ConstraintExplorerEntry]
    details_by_id: dict[str, ConstraintExplorerDetail]
    metadata: ConstraintQueryMetadata


class _ConstraintExplorerReadModelCache:
    def __init__(self) -> None:
        self._values: dict[_CacheKey, _ReadModel] = {}

    def get(self, key: _CacheKey) -> _ReadModel | None:
        return self._values.get(key)

    def set(self, key: _CacheKey, value: _ReadModel) -> _ReadModel:
        self._values[key] = value
        return value


class ConstraintExplorerService:
    """Builds a typed, query-first read model over constraint artifacts."""

    _query_spec = QuerySpec[ConstraintExplorerEntry](
        sort_fields={
            "operation_id": lambda item: item.operation_id,
            "property_path": lambda item: item.property_path,
            "source": lambda item: item.source.value,
            "section": lambda item: item.section,
            "constraint_kind": lambda item: item.constraint_kind.value,
            "agreement_status": lambda item: item.agreement_status.value,
        },
        group_fields={
            "source": lambda item: item.source.value,
            "operation_id": lambda item: item.operation_id,
            "section": lambda item: item.section,
            "constraint_kind": lambda item: item.constraint_kind.value,
            "source_type": lambda item: item.source_type,
            "agreement_status": lambda item: item.agreement_status.value,
            "assertion_available": lambda item: _bool_key(item.assertion_available),
        },
        search_fields=[
            lambda item: item.constraint_id,
            lambda item: item.operation_id,
            lambda item: item.property_path,
            lambda item: item.expression,
            lambda item: item.source.value,
            lambda item: item.section,
            lambda item: item.constraint_kind.value,
            lambda item: item.source_type,
            lambda item: item.parameter,
            lambda item: item.static_expression,
            lambda item: item.dynamic_expression,
            lambda item: item.combined_expression,
            lambda item: item.assertion_preview,
        ],
        default_sort=("operation_id", "property_path", "source", "section"),
    )

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository
        self._cache = _ConstraintExplorerReadModelCache()

    def list_entries(
        self,
        run_name: str,
        query: ConstraintExplorerQuery,
    ) -> ConstraintExplorerPage:
        read_model = self._read_model(run_name)
        filters = _filters_from_query(query)
        records = _filter_entries(read_model.entries, filters)
        page = query_items(records, spec=self._query_spec, options=query.options)
        return ConstraintExplorerPage(
            items=page.items,
            pagination=page.pagination,
            groups=page.groups,
            metadata=read_model.metadata,
        )

    def get_entry(self, run_name: str, constraint_id: str) -> ConstraintExplorerDetail:
        read_model = self._read_model(run_name)
        detail = read_model.details_by_id.get(constraint_id)
        if detail is None:
            raise ArtifactNotFound(f"Constraint entry not found: {constraint_id}")
        return detail

    def all_entries(self, run_name: str) -> list[ConstraintExplorerEntry]:
        return list(self._read_model(run_name).entries)

    def get_facets(
        self,
        run_name: str,
        query: ConstraintFacetsQuery,
    ) -> ConstraintFacets:
        read_model = self._read_model(run_name)
        filters = _filters_from_facets_query(query)
        records = _filter_entries(read_model.entries, filters)
        records = _search_entries(records, query.q)
        return ConstraintFacets(
            source=_facet(records, lambda item: item.source.value),
            operation_id=_facet(records, lambda item: item.operation_id),
            section=_facet(records, lambda item: item.section),
            constraint_kind=_facet(records, lambda item: item.constraint_kind.value),
            source_type=_facet(records, lambda item: item.source_type),
            agreement_status=_facet(records, lambda item: item.agreement_status.value),
            assertion_available=_facet(
                records, lambda item: _bool_key(item.assertion_available)
            ),
            metadata=read_model.metadata,
        )

    def _read_model(self, run_name: str) -> _ReadModel:
        self.repository.get_run(run_name)
        key = self._cache_key(run_name)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        return self._cache.set(key, self._build_read_model(run_name))

    def _cache_key(self, run_name: str) -> _CacheKey:
        signatures = tuple(
            (artifact_id, self.repository.artifact_signature(run_name, artifact_id))
            for artifact_id in _PARTICIPATING_ARTIFACTS
        )
        return run_name, signatures

    def _build_read_model(self, run_name: str) -> _ReadModel:
        static_constraints = _dedupe(self._static_constraints(run_name))
        dynamic_payload = _read_optional_json(
            self.repository, run_name, "dynamic_constraint_miner"
        )
        dynamic_constraints = _dedupe(_dynamic_constraints(dynamic_payload))
        assertions = _assertions(run_name, dynamic_payload, self.repository)

        new_combined_payload = _read_optional_json(
            self.repository, run_name, COMBINATION_SOURCE_ARTIFACT
        )
        if new_combined_payload is not None:
            try:
                combination_model = parse_combination_artifact(
                    new_combined_payload,
                    run_name=run_name,
                )
                combined_source = CombinedSource.COMBINE_CONSTRAINT_MINERS
                warnings = combination_model.summary.warnings
                combined_constraints = _combination_constraints(combination_model.entries)
            except InvalidArtifactRequest as exc:
                combined_source, warnings, combined_constraints = _legacy_combined_constraints(
                    self.repository,
                    run_name,
                    static_constraints,
                    dynamic_constraints,
                    extra_warnings=[str(exc), _COMBINATION_FALLBACK_WARNING],
                )
        else:
            combined_source, warnings, combined_constraints = _legacy_combined_constraints(
                self.repository,
                run_name,
                static_constraints,
                dynamic_constraints,
                extra_warnings=[],
            )

        combined_constraints = _dedupe(combined_constraints)
        all_constraints = _dedupe(
            [*static_constraints, *dynamic_constraints, *combined_constraints]
        )

        static_expressions = _source_expression_map(static_constraints)
        dynamic_expressions = _source_expression_map(dynamic_constraints)
        combined_expressions = _source_expression_map(combined_constraints)

        entries: list[ConstraintExplorerEntry] = []
        details_by_id: dict[str, ConstraintExplorerDetail] = {}
        for constraint in all_constraints:
            key = (constraint.operation_id, constraint.property_path)
            assertion = _assertion_for(assertions, key)
            entry = _explorer_entry(
                constraint,
                static_expression=static_expressions.get(key),
                dynamic_expression=dynamic_expressions.get(key),
                combined_expression=combined_expressions.get(key),
                assertion=assertion,
            )
            entries.append(entry)
            details_by_id[entry.constraint_id] = _detail_from_entry(entry, assertion)

        return _ReadModel(
            entries=sorted(
                entries,
                key=lambda item: (
                    item.operation_id,
                    item.property_path,
                    item.source.value,
                    item.section or "",
                    item.expression,
                ),
            ),
            details_by_id=details_by_id,
            metadata=ConstraintQueryMetadata(
                combined_source=combined_source,
                warnings=warnings,
            ),
        )

    def _static_constraints(self, run_name: str) -> list[_NormalizedConstraint]:
        constraints: list[_NormalizedConstraint] = []
        payload = _read_optional_json(self.repository, run_name, "static_constraint_miner")
        if isinstance(payload, dict):
            known_sections = {"common", "request_response", "response_properties"}
            if any(section in payload for section in known_sections):
                for section in ("common", "request_response", "response_properties"):
                    constraints.extend(
                        _operation_constraints(
                            payload.get(section),
                            source=ConstraintSource.STATIC,
                            section=section,
                            source_type=section,
                        )
                    )
            else:
                constraints.extend(
                    _operation_constraints(
                        payload,
                        source=ConstraintSource.STATIC,
                        section=None,
                        source_type="static_constraint_miner",
                    )
                )

        request_response_payload = _read_optional_json(
            self.repository,
            run_name,
            "static_constraint_miner_request_response",
        )
        constraints.extend(
            _operation_constraints(
                request_response_payload,
                source=ConstraintSource.STATIC,
                section="request_response",
                source_type="request_response",
            )
        )

        response_properties_payload = _read_optional_json(
            self.repository,
            run_name,
            "static_constraint_miner_response_properties",
        )
        constraints.extend(
            _operation_constraints(
                response_properties_payload,
                source=ConstraintSource.STATIC,
                section="response_properties",
                source_type="response_properties",
            )
        )
        return constraints


def _read_optional_json(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
    artifact_id: str,
) -> JsonValue | None:
    try:
        return repository.read_json_artifact(run_name, artifact_id)
    except ArtifactNotFound:
        return None


def _dynamic_constraints(payload: JsonValue | None) -> list[_NormalizedConstraint]:
    if not isinstance(payload, dict):
        return []
    return _operation_constraints(
        payload.get("constraints"),
        source=ConstraintSource.DYNAMIC,
        section=None,
        source_type="constraints",
    )


def _combined_constraints(payload: JsonValue | None) -> list[_NormalizedConstraint]:
    return _operation_constraints(
        payload,
        source=ConstraintSource.COMBINED,
        section=None,
        source_type="constraint_miner",
    )


def _combination_constraints(entries: list[CombinationEntry]) -> list[_NormalizedConstraint]:
    constraints: list[_NormalizedConstraint] = []
    for entry in entries:
        if entry.final_constraint is None:
            continue
        constraints.append(
            _NormalizedConstraint(
                source=ConstraintSource.COMBINED,
                operation_id=entry.operation_id,
                property_path=entry.property_path,
                expression=entry.final_constraint,
                section=None,
                parameter=None,
                source_type=COMBINATION_SOURCE_ARTIFACT,
            )
        )
    return constraints


def _legacy_combined_constraints(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
    static_constraints: list[_NormalizedConstraint],
    dynamic_constraints: list[_NormalizedConstraint],
    *,
    extra_warnings: list[str],
) -> tuple[CombinedSource, list[str], list[_NormalizedConstraint]]:
    combined_payload = _read_optional_json(repository, run_name, "constraint_miner")
    if combined_payload is None:
        return (
            CombinedSource.COMPUTED_FALLBACK,
            [*extra_warnings, _FALLBACK_WARNING],
            _computed_combined_constraints(static_constraints, dynamic_constraints),
        )
    return (
        CombinedSource.ARTIFACT,
        extra_warnings,
        _combined_constraints(combined_payload),
    )


def _operation_constraints(
    value: JsonValue | None,
    *,
    source: ConstraintSource,
    section: str | None,
    source_type: str | None,
) -> list[_NormalizedConstraint]:
    if not isinstance(value, dict):
        return []
    constraints: list[_NormalizedConstraint] = []
    for operation_id, raw_constraints in value.items():
        if isinstance(raw_constraints, dict):
            for property_path, expression in raw_constraints.items():
                constraints.append(
                    _NormalizedConstraint(
                        source=source,
                        operation_id=str(operation_id),
                        property_path=str(property_path),
                        expression=str(expression),
                        section=section,
                        parameter=None,
                        source_type=source_type,
                    )
                )
        elif isinstance(raw_constraints, list):
            for item in raw_constraints:
                if not isinstance(item, dict):
                    continue
                property_path = optional_str(item.get("property"))
                expression = optional_str(item.get("predicate"))
                if property_path is None or expression is None:
                    continue
                constraints.append(
                    _NormalizedConstraint(
                        source=source,
                        operation_id=str(operation_id),
                        property_path=property_path,
                        expression=expression,
                        section=section,
                        parameter=optional_str(item.get("parameter")),
                        source_type=source_type,
                    )
                )
    return constraints


def _computed_combined_constraints(
    static_constraints: list[_NormalizedConstraint],
    dynamic_constraints: list[_NormalizedConstraint],
) -> list[_NormalizedConstraint]:
    static_expressions = _source_expression_map(static_constraints)
    dynamic_expressions = _source_expression_map(dynamic_constraints)
    keys = sorted({*static_expressions, *dynamic_expressions})
    constraints: list[_NormalizedConstraint] = []
    for operation_id, property_path in keys:
        expression = static_expressions.get((operation_id, property_path))
        if expression is None:
            expression = dynamic_expressions[(operation_id, property_path)]
        constraints.append(
            _NormalizedConstraint(
                source=ConstraintSource.COMBINED,
                operation_id=operation_id,
                property_path=property_path,
                expression=expression,
                section=None,
                parameter=None,
                source_type="computed_fallback",
            )
        )
    return constraints


def _source_expression_map(
    constraints: list[_NormalizedConstraint],
) -> dict[_ConstraintKey, str]:
    expressions: dict[_ConstraintKey, set[str]] = {}
    for constraint in constraints:
        expressions.setdefault(
            (constraint.operation_id, constraint.property_path), set()
        ).add(constraint.expression)
    return {
        key: " | ".join(sorted(values))
        for key, values in sorted(expressions.items())
    }


def _explorer_entry(
    constraint: _NormalizedConstraint,
    *,
    static_expression: str | None,
    dynamic_expression: str | None,
    combined_expression: str | None,
    assertion: str | None,
) -> ConstraintExplorerEntry:
    has_static = static_expression is not None
    has_dynamic = dynamic_expression is not None
    return ConstraintExplorerEntry(
        constraint_id=_constraint_id(constraint),
        source=constraint.source,
        operation_id=constraint.operation_id,
        property_path=constraint.property_path,
        expression=constraint.expression,
        section=constraint.section,
        parameter=constraint.parameter,
        constraint_kind=_classify_constraint(constraint),
        source_type=constraint.source_type,
        static_expression=static_expression,
        dynamic_expression=dynamic_expression,
        combined_expression=combined_expression,
        has_static=has_static,
        has_dynamic=has_dynamic,
        agreement_status=_agreement_status(has_static, has_dynamic),
        assertion_available=assertion is not None,
        assertion_preview=_preview(assertion),
    )


def _detail_from_entry(
    entry: ConstraintExplorerEntry,
    assertion: str | None,
) -> ConstraintExplorerDetail:
    return ConstraintExplorerDetail(
        constraint_id=entry.constraint_id,
        source=entry.source,
        operation_id=entry.operation_id,
        property_path=entry.property_path,
        expression=entry.expression,
        section=entry.section,
        parameter=entry.parameter,
        constraint_kind=entry.constraint_kind,
        source_type=entry.source_type,
        static_expression=entry.static_expression,
        dynamic_expression=entry.dynamic_expression,
        combined_expression=entry.combined_expression,
        has_static=entry.has_static,
        has_dynamic=entry.has_dynamic,
        agreement_status=entry.agreement_status,
        assertion_available=entry.assertion_available,
        assertion_preview=entry.assertion_preview,
        assertion=assertion,
    )


def _constraint_id(constraint: _NormalizedConstraint) -> str:
    raw = "\x1f".join(
        [
            constraint.source.value,
            constraint.operation_id,
            constraint.property_path,
            constraint.expression,
            constraint.section or "",
            constraint.source_type or "",
        ]
    )
    return f"ctr_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _classify_constraint(constraint: _NormalizedConstraint) -> ConstraintKind:
    if constraint.source_type == "request_response":
        return ConstraintKind.REQUEST_RESPONSE_RELATION

    expression = constraint.expression.casefold()
    property_path = constraint.property_path.casefold()
    text = f"{property_path} {expression}"

    if "yyyy-mm-dd" in text or "date" in property_path and "match" in expression:
        return ConstraintKind.DATE_FORMAT
    if " one of " in expression or " in {" in expression or " enum" in text:
        return ConstraintKind.ENUM
    if any(marker in expression for marker in (">=", "<=", ">", "<")):
        return ConstraintKind.BOUNDS
    if "required" in expression or "!= null" in expression or ".to.exist" in expression:
        return ConstraintKind.REQUIRED
    if "url" in text or "uri" in text:
        return ConstraintKind.URL
    if "length" in text or "two-letter" in text:
        return ConstraintKind.FIXED_LENGTH
    if "==" in expression or "eql" in expression or "equals" in expression:
        return ConstraintKind.EQUALITY
    if "input." in expression and "return." in expression:
        return ConstraintKind.RELATION
    return ConstraintKind.UNKNOWN


def _agreement_status(has_static: bool, has_dynamic: bool) -> AgreementStatus:
    if has_static and has_dynamic:
        return AgreementStatus.BOTH_PRESENT
    if has_static:
        return AgreementStatus.STATIC_ONLY
    if has_dynamic:
        return AgreementStatus.DYNAMIC_ONLY
    return AgreementStatus.COMBINED_ONLY


def _filters_from_query(query: ConstraintExplorerQuery) -> _ConstraintFilters:
    return _ConstraintFilters(
        source=_enum_filter(ConstraintSource, query.source, "source"),
        operation_id=query.operation_id,
        section=query.section,
        property_path=query.property_path,
        property_prefix=query.property_prefix,
        constraint_kind=_enum_filter(
            ConstraintKind, query.constraint_kind, "constraint_kind"
        ),
        source_type=query.source_type,
        agreement_status=_enum_filter(
            AgreementStatus, query.agreement_status, "agreement_status"
        ),
        assertion_available=query.assertion_available,
    )


def _filters_from_facets_query(query: ConstraintFacetsQuery) -> _ConstraintFilters:
    return _ConstraintFilters(
        source=_enum_filter(ConstraintSource, query.source, "source"),
        operation_id=query.operation_id,
        section=query.section,
        property_path=query.property_path,
        property_prefix=query.property_prefix,
        constraint_kind=_enum_filter(
            ConstraintKind, query.constraint_kind, "constraint_kind"
        ),
        source_type=query.source_type,
        agreement_status=_enum_filter(
            AgreementStatus, query.agreement_status, "agreement_status"
        ),
        assertion_available=query.assertion_available,
    )


def _enum_filter(
    enum_type: type[_TEnum],
    value: str | None,
    field_name: str,
) -> _TEnum | None:
    if value is None:
        return None
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise InvalidArtifactRequest(
            f"Unsupported {field_name} '{value}'. Allowed values: {allowed}"
        ) from exc


def _filter_entries(
    entries: list[ConstraintExplorerEntry],
    filters: _ConstraintFilters,
) -> list[ConstraintExplorerEntry]:
    return [
        entry
        for entry in entries
        if (filters.source is None or entry.source == filters.source)
        and (filters.operation_id is None or entry.operation_id == filters.operation_id)
        and (filters.section is None or entry.section == filters.section)
        and (
            filters.property_path is None
            or entry.property_path == filters.property_path
        )
        and (
            filters.property_prefix is None
            or entry.property_path.startswith(filters.property_prefix)
        )
        and (
            filters.constraint_kind is None
            or entry.constraint_kind == filters.constraint_kind
        )
        and (filters.source_type is None or entry.source_type == filters.source_type)
        and (
            filters.agreement_status is None
            or entry.agreement_status == filters.agreement_status
        )
        and (
            filters.assertion_available is None
            or entry.assertion_available == filters.assertion_available
        )
    ]


def _search_entries(
    entries: list[ConstraintExplorerEntry],
    q: str | None,
) -> list[ConstraintExplorerEntry]:
    query = q.strip().casefold() if q else ""
    if not query:
        return entries
    return [
        entry
        for entry in entries
        if any(
            query in value.casefold()
            for value in (
                entry.constraint_id,
                entry.operation_id,
                entry.property_path,
                entry.expression,
                entry.source.value,
                entry.section,
                entry.constraint_kind.value,
                entry.source_type,
                entry.parameter,
                entry.static_expression,
                entry.dynamic_expression,
                entry.combined_expression,
                entry.assertion_preview,
            )
            if value is not None
        )
    ]


def _facet(
    entries: list[ConstraintExplorerEntry],
    accessor: Callable[[ConstraintExplorerEntry], str | None],
) -> list[ConstraintFacetBucket]:
    counts = Counter(value for entry in entries if (value := accessor(entry)))
    return [
        ConstraintFacetBucket(key=str(key), count=count)
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _dedupe(constraints: list[_NormalizedConstraint]) -> list[_NormalizedConstraint]:
    by_key: dict[tuple[str, str, str, str, str, str, str], _NormalizedConstraint] = {}
    for constraint in constraints:
        key = (
            constraint.source.value,
            constraint.operation_id,
            constraint.property_path,
            constraint.expression,
            constraint.section or "",
            constraint.source_type or "",
            constraint.parameter or "",
        )
        by_key[key] = constraint
    return sorted(
        by_key.values(),
        key=lambda item: (
            item.source.value,
            item.operation_id,
            item.property_path,
            item.section or "",
            item.expression,
        ),
    )


def _assertions(
    run_name: str,
    dynamic_payload: JsonValue | None,
    repository: ArtifactRepositoryProtocol,
) -> dict[_ConstraintKey, str]:
    assertions: dict[_ConstraintKey, str] = {}
    _collect_dynamic_assertions(assertions, dynamic_payload)
    try:
        rows = repository.read_csv_rows(run_name, "invariants_csv")
    except ArtifactNotFound:
        rows = []
    for row in rows:
        assertion = row.get("postmanAssertion")
        operation_id = operation_id_from_pptname(row.get("pptname"))
        variables = row.get("variables")
        if assertion is None or operation_id is None or variables is None:
            continue
        for variable in _split_variables(variables):
            _store_assertion(assertions, operation_id, variable, assertion)
    return assertions


def _collect_dynamic_assertions(
    assertions: dict[_ConstraintKey, str],
    dynamic_payload: JsonValue | None,
) -> None:
    if not isinstance(dynamic_payload, dict):
        return
    raw = dynamic_payload.get("raw")
    if isinstance(raw, list):
        _collect_raw_rows(assertions, None, raw)
    elif isinstance(raw, dict):
        for operation_id, rows in raw.items():
            if isinstance(rows, list):
                _collect_raw_rows(assertions, str(operation_id), rows)


def _collect_raw_rows(
    assertions: dict[_ConstraintKey, str],
    operation_id: str | None,
    rows: list[JsonValue],
) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        assertion = (
            optional_str(row.get("postmanAssertion"))
            or optional_str(row.get("postman_assertion"))
            or optional_str(row.get("assertion"))
        )
        row_operation_id = (
            optional_str(row.get("endpoint"))
            or optional_str(row.get("operation_id"))
            or operation_id_from_pptname(optional_str(row.get("pptname")))
            or operation_id
        )
        property_path = (
            optional_str(row.get("variable"))
            or optional_str(row.get("property"))
            or optional_str(row.get("property_path"))
            or optional_str(row.get("response_container_path"))
        )
        if assertion is None or row_operation_id is None or property_path is None:
            continue
        _store_assertion(assertions, row_operation_id, property_path, assertion)


def _store_assertion(
    assertions: dict[_ConstraintKey, str],
    operation_id: str,
    property_path: str,
    assertion: str,
) -> None:
    for variant in _property_path_variants(property_path):
        assertions.setdefault((operation_id, variant), assertion)


def _assertion_for(
    assertions: dict[_ConstraintKey, str],
    key: _ConstraintKey,
) -> str | None:
    operation_id, property_path = key
    for variant in _property_path_variants(property_path):
        assertion = assertions.get((operation_id, variant))
        if assertion is not None:
            return assertion
    return None


def _property_path_variants(property_path: str) -> list[str]:
    stripped = property_path.strip()
    if stripped.startswith("(") and stripped.endswith(")"):
        stripped = stripped[1:-1].strip()
    variants = {
        property_path,
        stripped,
        property_path.replace("[]", ""),
        stripped.replace("[]", ""),
    }
    return [variant for variant in variants if variant]


def _split_variables(variables: str) -> list[str]:
    stripped = variables.strip()
    if stripped.startswith("(") and stripped.endswith(")"):
        stripped = stripped[1:-1]
    return [
        variable.strip()
        for variable in re.split(r"\s*,\s*", stripped)
        if variable.strip()
    ]


def _preview(assertion: str | None) -> str | None:
    if assertion is None:
        return None
    if len(assertion) <= _ASSERTION_PREVIEW_LIMIT:
        return assertion
    return f"{assertion[: _ASSERTION_PREVIEW_LIMIT - 3]}..."


def _bool_key(value: bool) -> str:
    return "true" if value else "false"
