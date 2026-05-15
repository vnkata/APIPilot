"""Operation read models derived from normalized OpenAPI artifacts."""

from __future__ import annotations

from collections import Counter

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    OperationExplorerQuery,
    OperationFacetsQuery,
    QueryOptions,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.explorer_index import (
    RunExplorerIndexService,
)
from api_testing.backend.application.read_services.utils import (
    http_method,
    optional_str,
)
from api_testing.backend.domain.errors import ArtifactNotFound
from api_testing.backend.domain.models import (
    ConstraintFacetBucket,
    GraphEdgeStatus,
    GroupedPage,
    OperationCountSummary,
    OperationDetail,
    OperationExplorerDetail,
    OperationExplorerEntry,
    OperationExplorerPage,
    OperationFacets,
    OperationGraphSummary,
    OperationSummary,
)


class OperationQueryService:
    """Builds operation summaries and details from specification artifacts."""

    _explorer_spec = QuerySpec[OperationExplorerEntry](
        sort_fields={
            "operation_key": lambda item: item.operation_key,
            "operation_id": lambda item: item.operation_id,
            "http_method": lambda item: item.http_method.value if item.http_method else None,
            "path_template": lambda item: item.path_template,
            "constraint_count": lambda item: item.constraint_count,
            "invariant_count": lambda item: item.invariant_count,
            "graph_in_degree": lambda item: item.graph_in_degree,
            "graph_out_degree": lambda item: item.graph_out_degree,
            "test_case_count": lambda item: item.test_case_count,
        },
        group_fields={
            "http_method": lambda item: item.http_method.value if item.http_method else None,
            "has_request_body": lambda item: _bool_key(_has_request_body_entry(item)),
            "has_constraints": lambda item: _bool_key(item.constraint_count > 0),
            "has_invariants": lambda item: _bool_key(item.invariant_count > 0),
            "has_graph_edges": lambda item: _bool_key(
                item.graph_in_degree + item.graph_out_degree > 0
            ),
            "has_failures": lambda item: _bool_key(item.has_failures),
        },
        search_fields=[
            lambda item: item.operation_key,
            lambda item: item.operation_id,
            lambda item: item.display_operation_id,
            lambda item: item.http_method.value if item.http_method else None,
            lambda item: item.path_template,
        ],
        default_sort=("operation_id",),
    )

    def __init__(
        self,
        repository: ArtifactRepositoryProtocol,
        index_service: RunExplorerIndexService | None = None,
    ) -> None:
        self.repository = repository
        self.index_service = index_service
        self.invariant_explorer = None
        self.graph_service = None

    def configure_explorer_dependencies(
        self,
        *,
        invariant_explorer,
        graph_service,
    ) -> None:
        self.invariant_explorer = invariant_explorer
        self.graph_service = graph_service

    def list_operations(self, run_name: str) -> list[OperationSummary]:
        operations = self._operations(run_name)
        return sorted(
            [
                self._operation_summary(operation_id, operation)
                for operation_id, operation in operations.items()
            ],
            key=lambda item: item.operation_id,
        )

    def get_operation(self, run_name: str, operation_id: str) -> OperationDetail:
        operations = self._operations(run_name)
        if operation_id not in operations:
            raise ArtifactNotFound(f"Operation not found: {operation_id}")
        operation = operations[operation_id]
        summary = self._operation_summary(operation_id, operation)
        operation_map = operation if isinstance(operation, dict) else {}
        parameters = operation_map.get("parameters", {})
        responses = operation_map.get("responses", {})
        return OperationDetail(
            operation_id=summary.operation_id,
            display_operation_id=summary.display_operation_id,
            http_method=summary.http_method,
            path_template=summary.path_template,
            parameter_count=summary.parameter_count,
            response_statuses=summary.response_statuses,
            parameters=parameters if isinstance(parameters, dict) else {},
            request_body=operation_map.get("request_body"),
            responses=responses if isinstance(responses, dict) else {},
        )

    def list_explorer_entries(
        self,
        run_name: str,
        query: OperationExplorerQuery,
    ) -> OperationExplorerPage:
        records = _filter_operations(
            self._explorer_entries(run_name),
            query,
            self._response_status_counts(run_name),
        )
        page = query_items(records, spec=self._explorer_spec, options=query.options)
        return OperationExplorerPage(
            items=page.items,
            pagination=page.pagination,
            groups=page.groups,
        )

    def get_explorer_entry(
        self,
        run_name: str,
        operation_key: str,
    ) -> OperationExplorerDetail:
        index = self._index(run_name)
        operation_id = index.operation_id_for_key(operation_key)
        if operation_id is None:
            raise ArtifactNotFound(f"Operation entry not found: {operation_key}")
        operation = self.get_operation(run_name, operation_id)
        entry = next(
            item
            for item in self._explorer_entries(run_name)
            if item.operation_key == operation_key
        )
        constraints = index.constraints_by_operation.get(operation_id, [])
        invariants = [
            item
            for item in self._invariant_entries(run_name)
            if item.operation_id == operation_id
        ]
        incoming, outgoing = self._graph_edges_for_operation(run_name, operation_id)
        return OperationExplorerDetail(
            operation_id=entry.operation_id,
            display_operation_id=entry.display_operation_id,
            http_method=entry.http_method,
            path_template=entry.path_template,
            parameter_count=entry.parameter_count,
            response_statuses=entry.response_statuses,
            operation_key=entry.operation_key,
            response_status_count=entry.response_status_count,
            constraint_count=entry.constraint_count,
            invariant_count=entry.invariant_count,
            graph_in_degree=entry.graph_in_degree,
            graph_out_degree=entry.graph_out_degree,
            test_case_count=entry.test_case_count,
            has_failures=entry.has_failures,
            parameters=operation.parameters,
            request_body=operation.request_body,
            responses=operation.responses,
            constraint_summary=OperationCountSummary(
                total=len(constraints),
                by_kind=dict(Counter(item.constraint_kind.value for item in constraints)),
            ),
            invariant_summary=OperationCountSummary(
                total=len(invariants),
                by_kind=dict(Counter(item.invariant_kind.value for item in invariants)),
            ),
            graph_summary=OperationGraphSummary(
                in_degree=len(incoming),
                out_degree=len(outgoing),
                incoming_edge_count=len(incoming),
                outgoing_edge_count=len(outgoing),
            ),
            report_status_counts=index.report_status_counts.get(operation_id, {}),
            test_case_status_counts=index.test_case_status_counts.get(operation_id, {}),
            related_constraint_ids=[item.constraint_id for item in constraints],
            related_invariant_ids=[item.invariant_id for item in invariants],
            incoming_edge_ids=[item.edge_id for item in incoming],
            outgoing_edge_ids=[item.edge_id for item in outgoing],
        )

    def get_explorer_facets(
        self,
        run_name: str,
        query: OperationFacetsQuery,
    ) -> OperationFacets:
        query_options = QueryOptions(q=query.q, limit=10_000, offset=0)
        entries = _filter_operations(
            self._explorer_entries(run_name),
            OperationExplorerQuery(
                options=query_options,
                operation_id=query.operation_id,
                http_method=query.http_method,
                response_status=query.response_status,
                has_request_body=query.has_request_body,
                has_constraints=query.has_constraints,
                has_invariants=query.has_invariants,
                has_graph_edges=query.has_graph_edges,
                has_failures=query.has_failures,
            ),
            self._response_status_counts(run_name),
        )
        if query.q:
            entries = query_items(
                entries,
                spec=self._explorer_spec,
                options=query_options,
            ).items
        return OperationFacets(
            http_method=_facet(
                entries, lambda item: item.http_method.value if item.http_method else None
            ),
            response_status=_status_facet(entries, self._response_status_counts(run_name)),
            has_request_body=_facet(
                entries, lambda item: _bool_key(_has_request_body(run_name, self, item.operation_id))
            ),
            has_constraints=_facet(entries, lambda item: _bool_key(item.constraint_count > 0)),
            has_invariants=_facet(entries, lambda item: _bool_key(item.invariant_count > 0)),
            has_graph_edges=_facet(
                entries,
                lambda item: _bool_key(item.graph_in_degree + item.graph_out_degree > 0),
            ),
            has_failures=_facet(entries, lambda item: _bool_key(item.has_failures)),
        )

    def _operations(self, run_name: str) -> dict[str, JsonValue]:
        raw = self.repository.read_json_artifact(run_name, "specification")
        spec = raw if isinstance(raw, dict) else {}
        operations = spec.get("operations", {})
        return operations if isinstance(operations, dict) else {}

    def _operation_summary(
        self,
        operation_id: str,
        operation: JsonValue,
    ) -> OperationSummary:
        operation_map = operation if isinstance(operation, dict) else {}
        parameters = operation_map.get("parameters", {})
        responses = operation_map.get("responses", {})
        return OperationSummary(
            operation_id=operation_id,
            display_operation_id=optional_str(operation_map.get("operation_id")),
            http_method=http_method(operation_map.get("http_method")),
            path_template=optional_str(
                operation_map.get("endpoint_path") or operation_map.get("path")
            ),
            parameter_count=len(parameters) if isinstance(parameters, dict) else 0,
            response_statuses=sorted(str(status) for status in responses)
            if isinstance(responses, dict)
            else [],
        )

    def _explorer_entries(self, run_name: str) -> list[OperationExplorerEntry]:
        index = self._index(run_name)
        invariants_by_operation = Counter(
            item.operation_id
            for item in self._invariant_entries(run_name)
            if item.operation_id is not None
        )
        graph_in, graph_out = self._graph_degree_counts(run_name)
        entries: list[OperationExplorerEntry] = []
        for operation in self.list_operations(run_name):
            report_statuses = index.report_status_counts.get(operation.operation_id, {})
            test_statuses = index.test_case_status_counts.get(operation.operation_id, {})
            entries.append(
                OperationExplorerEntry(
                    operation_id=operation.operation_id,
                    display_operation_id=operation.display_operation_id,
                    http_method=operation.http_method,
                    path_template=operation.path_template,
                    parameter_count=operation.parameter_count,
                    response_statuses=operation.response_statuses,
                    operation_key=index.operation_key(operation.operation_id),
                    response_status_count=len(operation.response_statuses),
                    constraint_count=len(
                        index.constraints_by_operation.get(operation.operation_id, [])
                    ),
                    invariant_count=invariants_by_operation[operation.operation_id],
                    graph_in_degree=graph_in[operation.operation_id],
                    graph_out_degree=graph_out[operation.operation_id],
                    test_case_count=sum(test_statuses.values()),
                    has_failures=_has_failure(report_statuses, test_statuses),
                )
            )
        return entries

    def _index(self, run_name: str):
        if self.index_service is None:
            raise RuntimeError("Operation explorer index service was not configured")
        return self.index_service.get_index(run_name)

    def _invariant_entries(self, run_name: str):
        if self.invariant_explorer is None:
            return []
        return self.invariant_explorer.all_entries(run_name)

    def _graph_edges_for_operation(self, run_name: str, operation_id: str):
        if self.graph_service is None:
            return [], []
        from api_testing.backend.application.querying import GraphEdgeExplorerQuery

        page = self.graph_service.list_graph_edges(
            run_name,
            GraphEdgeExplorerQuery(
                options=QueryOptions(limit=10_000, offset=0),
                edge_status="all",
            ),
        )
        incoming = [item for item in page.items if item.to_operation_id == operation_id]
        outgoing = [item for item in page.items if item.from_operation_id == operation_id]
        return incoming, outgoing

    def _graph_degree_counts(self, run_name: str) -> tuple[Counter[str], Counter[str]]:
        if self.graph_service is None:
            return Counter(), Counter()
        from api_testing.backend.application.querying import GraphEdgeExplorerQuery

        page = self.graph_service.list_graph_edges(
            run_name,
            GraphEdgeExplorerQuery(
                options=QueryOptions(limit=10_000, offset=0),
                edge_status="all",
            ),
        )
        in_counts: Counter[str] = Counter()
        out_counts: Counter[str] = Counter()
        for edge in page.items:
            in_counts[edge.to_operation_id] += 1
            out_counts[edge.from_operation_id] += 1
        return in_counts, out_counts

    def _response_status_counts(self, run_name: str) -> dict[str, dict[str, int]]:
        return self._index(run_name).report_status_counts


def _filter_operations(
    entries: list[OperationExplorerEntry],
    query: OperationExplorerQuery,
    response_status_counts: dict[str, dict[str, int]],
) -> list[OperationExplorerEntry]:
    return [
        entry
        for entry in entries
        if (query.operation_id is None or entry.operation_id == query.operation_id)
        and (query.operation_key is None or entry.operation_key == query.operation_key)
        and (
            query.http_method is None
            or (entry.http_method is not None and entry.http_method.value == query.http_method)
        )
        and (
            query.response_status is None
            or query.response_status in response_status_counts.get(entry.operation_id, {})
            or query.response_status in entry.response_statuses
        )
        and (
            query.has_request_body is None
            or _has_request_body_entry(entry) == query.has_request_body
        )
        and (
            query.has_constraints is None
            or (entry.constraint_count > 0) == query.has_constraints
        )
        and (
            query.has_invariants is None
            or (entry.invariant_count > 0) == query.has_invariants
        )
        and (
            query.has_graph_edges is None
            or (entry.graph_in_degree + entry.graph_out_degree > 0)
            == query.has_graph_edges
        )
        and (query.has_failures is None or entry.has_failures == query.has_failures)
    ]


def _has_failure(
    report_statuses: dict[str, int],
    test_statuses: dict[str, int],
) -> bool:
    return any(_is_failure_status(status) for status in [*report_statuses, *test_statuses])


def _is_failure_status(status: str) -> bool:
    try:
        return int(status) >= 400
    except ValueError:
        return False


def _has_request_body_entry(entry: OperationExplorerEntry) -> bool:
    return entry.http_method is not None and entry.http_method.value in {"post", "put", "patch"}


def _has_request_body(
    run_name: str,
    service: OperationQueryService,
    operation_id: str,
) -> bool:
    operation = service.get_operation(run_name, operation_id)
    return bool(operation.request_body)


def _facet(entries: list[OperationExplorerEntry], accessor) -> list[ConstraintFacetBucket]:
    counts = Counter(value for entry in entries if (value := accessor(entry)))
    return [
        ConstraintFacetBucket(key=str(key), count=count)
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _status_facet(
    entries: list[OperationExplorerEntry],
    status_counts: dict[str, dict[str, int]],
) -> list[ConstraintFacetBucket]:
    counts: Counter[str] = Counter()
    for entry in entries:
        for status, count in status_counts.get(entry.operation_id, {}).items():
            counts[status] += count
    return [
        ConstraintFacetBucket(key=status, count=count)
        for status, count in sorted(counts.items())
    ]


def _bool_key(value: bool) -> str:
    return "true" if value else "false"
