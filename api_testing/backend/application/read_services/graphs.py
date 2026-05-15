"""Dependency graph and graph explorer read services."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from typing import TypeVar

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    GraphEdgeExplorerQuery,
    GraphEdgeQuery,
    GraphFacetsQuery,
    GraphNodeQuery,
    GraphSequenceQuery,
    QueryOptions,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.explorer_index import (
    RunExplorerIndex,
    RunExplorerIndexService,
)
from api_testing.backend.application.read_services.utils import (
    graph_similarities,
    http_method,
    optional_str,
)
from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.backend.domain.models import (
    ConstraintFacetBucket,
    DependencyGraph,
    GraphEdge,
    GraphEdgeDetail,
    GraphEdgeStatus,
    GraphEvidence,
    GraphEvidenceSource,
    GraphExplorerEdge,
    GraphFacets,
    GraphNode,
    GraphNodeKind,
    GraphSequence,
    GraphSequenceParameterSource,
    GroupedPage,
)


_GRAPH_ARTIFACTS = (
    "semantic_property_dependency_graph",
    "heuristic_edges",
    "gpt_edges",
    "dependency_sequences",
    "specification",
)
_FileSignature = tuple[int, int]
_CacheKey = tuple[str, tuple[tuple[str, _FileSignature | None], ...]]
_EdgeKey = tuple[str, str]
_TEnum = TypeVar("_TEnum", GraphNodeKind, GraphEdgeStatus, GraphEvidenceSource)


@dataclass(frozen=True, slots=True)
class _GraphReadModel:
    legacy_graph: DependencyGraph
    nodes: list[GraphNode]
    edges: list[GraphExplorerEdge]
    details_by_id: dict[str, GraphEdgeDetail]
    sequences: list[GraphSequence]
    sequences_by_id: dict[str, GraphSequence]


@dataclass(frozen=True, slots=True)
class _EdgeSeed:
    source: GraphEvidenceSource
    source_artifact_id: str
    from_operation_id: str
    to_operation_id: str
    similar_parameters: JsonValue


@dataclass(frozen=True, slots=True)
class _NodeSeed:
    operation_id: str
    label: str
    node_kind: GraphNodeKind
    property_path: str | None = None
    parameter_name: str | None = None


@dataclass(frozen=True, slots=True)
class _GraphNodeFilters:
    node_kind: GraphNodeKind | None
    operation_id: str | None


@dataclass(frozen=True, slots=True)
class _GraphEdgeFilters:
    edge_status: GraphEdgeStatus | None
    include_all_statuses: bool
    evidence_source: GraphEvidenceSource | None
    from_operation_id: str | None
    to_operation_id: str | None


@dataclass(frozen=True, slots=True)
class _GraphSequenceFilters:
    target_operation_id: str | None
    operation_id: str | None
    sequence_type: str | None


class DependencyGraphQueryService:
    """Builds aggregate, detailed, and explorer graph read models."""

    _node_spec = QuerySpec[GraphNode](
        sort_fields={
            "node_id": lambda item: item.node_id,
            "node_kind": lambda item: item.node_kind.value,
            "operation_id": lambda item: item.operation_id,
            "label": lambda item: item.label,
            "in_degree": lambda item: item.in_degree,
            "out_degree": lambda item: item.out_degree,
        },
        group_fields={
            "node_kind": lambda item: item.node_kind.value,
            "operation_id": lambda item: item.operation_id,
        },
        search_fields=[
            lambda item: item.node_id,
            lambda item: item.node_kind.value,
            lambda item: item.operation_id,
            lambda item: item.label,
            lambda item: item.property_path,
            lambda item: item.parameter_name,
        ],
        default_sort=("node_kind", "operation_id", "label"),
    )
    _edge_spec = QuerySpec[GraphExplorerEdge](
        sort_fields={
            "from_node": lambda item: item.from_node,
            "to_node": lambda item: item.to_node,
            "from_operation_id": lambda item: item.from_operation_id,
            "to_operation_id": lambda item: item.to_operation_id,
            "edge_status": lambda item: item.edge_status.value,
            "evidence_count": lambda item: item.evidence_count,
        },
        group_fields={
            "from_node": lambda item: item.from_node,
            "to_node": lambda item: item.to_node,
            "from_operation_id": lambda item: item.from_operation_id,
            "to_operation_id": lambda item: item.to_operation_id,
            "edge_status": lambda item: item.edge_status.value,
        },
        search_fields=[
            lambda item: item.edge_id,
            lambda item: item.from_operation_id,
            lambda item: item.to_operation_id,
            lambda item: item.from_node,
            lambda item: item.to_node,
            lambda item: item.edge_status.value,
            lambda item: " ".join(item.evidence_sources),
            lambda item: " ".join(item.evidence_preview),
        ],
        default_sort=("from_operation_id", "to_operation_id", "edge_status"),
    )
    _sequence_spec = QuerySpec[GraphSequence](
        sort_fields={
            "sequence_id": lambda item: item.sequence_id,
            "target_operation_id": lambda item: item.target_operation_id,
            "sequence_type": lambda item: item.sequence_type,
            "length": lambda item: item.length,
            "score": lambda item: item.score,
        },
        group_fields={
            "target_operation_id": lambda item: item.target_operation_id,
            "sequence_type": lambda item: item.sequence_type,
        },
        search_fields=[
            lambda item: item.sequence_id,
            lambda item: item.target_operation_id,
            lambda item: item.sequence_type,
            lambda item: " ".join(item.operations),
        ],
        default_sort=("target_operation_id", "sequence_type", "length"),
    )

    def __init__(
        self,
        repository: ArtifactRepositoryProtocol,
        index_service: RunExplorerIndexService,
    ) -> None:
        self.repository = repository
        self.index_service = index_service
        self._values: dict[_CacheKey, _GraphReadModel] = {}

    def get_dependency_graph(self, run_name: str) -> DependencyGraph:
        return self._read_model(run_name).legacy_graph

    def list_graph_edges(
        self,
        run_name: str,
        query: GraphEdgeQuery | GraphEdgeExplorerQuery,
    ) -> GroupedPage[GraphExplorerEdge]:
        explorer_query = _edge_explorer_query(query)
        records = _filter_edges(
            self._read_model(run_name).edges,
            _edge_filters_from_query(explorer_query),
        )
        return query_items(records, spec=self._edge_spec, options=explorer_query.options)

    def get_graph_edge(self, run_name: str, edge_id: str) -> GraphEdgeDetail:
        detail = self._read_model(run_name).details_by_id.get(edge_id)
        if detail is None:
            raise ArtifactNotFound(f"Graph edge not found: {edge_id}")
        return detail

    def list_graph_nodes(
        self,
        run_name: str,
        query: GraphNodeQuery,
    ) -> GroupedPage[GraphNode]:
        records = _filter_nodes(
            self._read_model(run_name).nodes,
            _node_filters_from_query(query),
        )
        return query_items(records, spec=self._node_spec, options=query.options)

    def list_graph_sequences(
        self,
        run_name: str,
        query: GraphSequenceQuery,
    ) -> GroupedPage[GraphSequence]:
        records = _filter_sequences(
            self._read_model(run_name).sequences,
            _sequence_filters_from_query(query),
        )
        return query_items(records, spec=self._sequence_spec, options=query.options)

    def get_graph_sequence(self, run_name: str, sequence_id: str) -> GraphSequence:
        sequence = self._read_model(run_name).sequences_by_id.get(sequence_id)
        if sequence is None:
            raise ArtifactNotFound(f"Graph sequence not found: {sequence_id}")
        return sequence

    def get_graph_facets(
        self,
        run_name: str,
        query: GraphFacetsQuery,
    ) -> GraphFacets:
        read_model = self._read_model(run_name)
        edge_filters = _edge_filters_from_facets_query(query)
        node_filters = _node_filters_from_facets_query(query)
        sequence_filters = _sequence_filters_from_facets_query(query)
        edges = _search_edges(_filter_edges(read_model.edges, edge_filters), query.q)
        nodes = _search_nodes(_filter_nodes(read_model.nodes, node_filters), query.q)
        sequences = _search_sequences(
            _filter_sequences(read_model.sequences, sequence_filters), query.q
        )
        return GraphFacets(
            edge_status=_facet(edges, lambda item: item.edge_status.value),
            evidence_source=_evidence_source_facet(edges),
            from_operation_id=_facet(edges, lambda item: item.from_operation_id),
            to_operation_id=_facet(edges, lambda item: item.to_operation_id),
            node_kind=_facet(nodes, lambda item: item.node_kind.value),
            sequence_type=_facet(sequences, lambda item: item.sequence_type),
        )

    def _read_model(self, run_name: str) -> _GraphReadModel:
        self.repository.get_run(run_name)
        key = self._cache_key(run_name)
        cached = self._values.get(key)
        if cached is not None:
            return cached
        model = self._build_read_model(run_name)
        self._values[key] = model
        return model

    def _cache_key(self, run_name: str) -> _CacheKey:
        return (
            run_name,
            tuple(
                (artifact_id, self.repository.artifact_signature(run_name, artifact_id))
                for artifact_id in _GRAPH_ARTIFACTS
            ),
        )

    def _build_read_model(self, run_name: str) -> _GraphReadModel:
        index = self.index_service.get_index(run_name)
        final_graph = _read_graph_payload(self.repository, run_name)
        legacy_graph = _legacy_graph(run_name, final_graph)
        seeds = [
            *_edge_seeds(final_graph, GraphEvidenceSource.FINAL_GRAPH, "semantic_property_dependency_graph"),
            *_edge_seeds(
                _read_optional_json(self.repository, run_name, "heuristic_edges"),
                GraphEvidenceSource.HEURISTIC_EDGES,
                "heuristic_edges",
            ),
            *_edge_seeds(
                _read_optional_json(self.repository, run_name, "gpt_edges"),
                GraphEvidenceSource.GPT_EDGES,
                "gpt_edges",
            ),
        ]
        final_keys = {
            (seed.from_operation_id, seed.to_operation_id)
            for seed in seeds
            if seed.source == GraphEvidenceSource.FINAL_GRAPH
        }
        details = _build_edge_details(seeds, final_keys, index)
        details_by_id = {detail.edge_id: detail for detail in details}
        nodes = _build_nodes(index, details)
        sequences = _graph_sequences(
            _read_optional_json(self.repository, run_name, "dependency_sequences")
        )
        return _GraphReadModel(
            legacy_graph=legacy_graph,
            nodes=nodes,
            edges=[_edge_from_detail(detail) for detail in details],
            details_by_id=details_by_id,
            sequences=sequences,
            sequences_by_id={sequence.sequence_id: sequence for sequence in sequences},
        )


def _edge_explorer_query(
    query: GraphEdgeQuery | GraphEdgeExplorerQuery,
) -> GraphEdgeExplorerQuery:
    if isinstance(query, GraphEdgeExplorerQuery):
        return query
    return GraphEdgeExplorerQuery(
        options=query.options,
        from_operation_id=query.from_node,
        to_operation_id=query.to_node,
    )


def _read_graph_payload(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
) -> JsonValue:
    return _read_optional_json(repository, run_name, "semantic_property_dependency_graph")


def _legacy_graph(run_name: str, raw: JsonValue) -> DependencyGraph:
    graph = raw if isinstance(raw, dict) else {}
    nodes_raw = graph.get("nodes", [])
    edges_raw = graph.get("edges", [])
    nodes = [str(node) for node in nodes_raw] if isinstance(nodes_raw, list) else []
    edges: list[GraphEdge] = []
    if isinstance(edges_raw, list):
        for edge in edges_raw:
            if not isinstance(edge, dict):
                continue
            edges.append(
                GraphEdge(
                    from_node=str(edge.get("from_node", "")),
                    to_node=str(edge.get("to_node", "")),
                    similar_parameters=graph_similarities(
                        edge.get("similar_parameters", [])
                    ),
                )
            )
    return DependencyGraph(run_name=run_name, nodes=sorted(nodes), edges=edges)


def _edge_seeds(
    raw: JsonValue,
    source: GraphEvidenceSource,
    source_artifact_id: str,
) -> list[_EdgeSeed]:
    if isinstance(raw, dict):
        edges_raw = raw.get("edges", [])
    else:
        edges_raw = raw
    records = edges_raw if isinstance(edges_raw, list) else []
    seeds: list[_EdgeSeed] = []
    for edge in records:
        if not isinstance(edge, dict):
            continue
        from_node = edge.get("from_node")
        to_node = edge.get("to_node")
        if from_node is None or to_node is None:
            continue
        seeds.append(
            _EdgeSeed(
                source=source,
                source_artifact_id=source_artifact_id,
                from_operation_id=str(from_node),
                to_operation_id=str(to_node),
                similar_parameters=edge.get("similar_parameters", []),
            )
        )
    return seeds


def _build_edge_details(
    seeds: list[_EdgeSeed],
    final_keys: set[_EdgeKey],
    index: RunExplorerIndex,
) -> list[GraphEdgeDetail]:
    grouped: dict[_EdgeKey, list[_EdgeSeed]] = defaultdict(list)
    for seed in seeds:
        grouped[(seed.from_operation_id, seed.to_operation_id)].append(seed)

    details: list[GraphEdgeDetail] = []
    for (from_operation_id, to_operation_id), edge_seeds in grouped.items():
        status = (
            GraphEdgeStatus.FINAL
            if (from_operation_id, to_operation_id) in final_keys
            else GraphEdgeStatus.CANDIDATE
        )
        evidence = _evidence(edge_seeds, index)
        edge_id = _id("edge", from_operation_id, to_operation_id, status.value)
        similar_parameters = graph_similarities(
            [
                {
                    "value1": item.value1,
                    "value2": item.value2,
                    "in_value": item.relation_hint,
                }
                for item in evidence
            ]
        )
        details.append(
            GraphEdgeDetail(
                from_node=from_operation_id,
                to_node=to_operation_id,
                similar_parameters=similar_parameters,
                edge_id=edge_id,
                edge_status=status,
                from_operation_id=from_operation_id,
                to_operation_id=to_operation_id,
                from_node_id=index.operation_key(from_operation_id),
                to_node_id=index.operation_key(to_operation_id),
                evidence_count=len(evidence),
                evidence_sources=sorted({item.source.value for item in evidence}),
                evidence_preview=[
                    _evidence_preview(item) for item in evidence[:3]
                ],
                evidence=evidence,
            )
        )
    return sorted(
        details,
        key=lambda item: (
            item.from_operation_id,
            item.to_operation_id,
            item.edge_status.value,
        ),
    )


def _evidence(
    seeds: list[_EdgeSeed],
    index: RunExplorerIndex,
) -> list[GraphEvidence]:
    evidence: list[GraphEvidence] = []
    for seed in seeds:
        similarities = (
            seed.similar_parameters if isinstance(seed.similar_parameters, list) else []
        )
        for position, item in enumerate(similarities):
            if not isinstance(item, dict):
                continue
            value1 = _optional_str(item.get("value1"))
            value2 = _optional_str(item.get("value2"))
            relation_hint = _optional_str(item.get("in_value"))
            evidence.append(
                GraphEvidence(
                    evidence_id=_id(
                        "ev",
                        seed.source_artifact_id,
                        seed.from_operation_id,
                        seed.to_operation_id,
                        str(position),
                        value1 or "",
                        value2 or "",
                        relation_hint or "",
                    ),
                    source=seed.source,
                    source_artifact_id=seed.source_artifact_id,
                    value1=value1,
                    value2=value2,
                    relation_hint=relation_hint,
                    from_evidence_node_id=_node_id_for_value(
                        index, seed.from_operation_id, value1
                    ),
                    to_evidence_node_id=_node_id_for_value(
                        index, seed.to_operation_id, value2
                    ),
                )
            )
    return evidence


def _build_nodes(index: RunExplorerIndex, details: list[GraphEdgeDetail]) -> list[GraphNode]:
    operation_edges_in: Counter[str] = Counter()
    operation_edges_out: Counter[str] = Counter()
    seeds: dict[str, _NodeSeed] = {}
    for operation_id in index.operations:
        seeds[index.operation_key(operation_id)] = _NodeSeed(
            operation_id=operation_id,
            label=operation_id,
            node_kind=GraphNodeKind.OPERATION,
        )
    for detail in details:
        operation_edges_out[detail.from_operation_id] += 1
        operation_edges_in[detail.to_operation_id] += 1
        for evidence in detail.evidence:
            _add_value_node(seeds, index, detail.from_operation_id, evidence.value1)
            _add_value_node(seeds, index, detail.to_operation_id, evidence.value2)

    nodes: list[GraphNode] = []
    for node_id, seed in seeds.items():
        operation = index.operations.get(seed.operation_id)
        operation_map = operation if isinstance(operation, dict) else {}
        nodes.append(
            GraphNode(
                node_id=node_id,
                node_kind=seed.node_kind,
                operation_id=seed.operation_id,
                label=seed.label,
                property_path=seed.property_path,
                parameter_name=seed.parameter_name,
                http_method=http_method(operation_map.get("http_method")),
                path_template=optional_str(
                    operation_map.get("endpoint_path") or operation_map.get("path")
                ),
                in_degree=operation_edges_in[seed.operation_id],
                out_degree=operation_edges_out[seed.operation_id],
            )
        )
    return sorted(nodes, key=lambda item: (item.node_kind.value, item.operation_id, item.label))


def _add_value_node(
    seeds: dict[str, _NodeSeed],
    index: RunExplorerIndex,
    operation_id: str,
    value: str | None,
) -> None:
    if value is None:
        return
    kind = _value_node_kind(index, operation_id, value)
    node_id = _node_id(operation_id, kind, value)
    if node_id in seeds:
        return
    seeds[node_id] = _NodeSeed(
        operation_id=operation_id,
        label=value,
        node_kind=kind,
        property_path=value if kind == GraphNodeKind.PROPERTY else None,
        parameter_name=value if kind == GraphNodeKind.PARAMETER else None,
    )


def _node_id_for_value(
    index: RunExplorerIndex,
    operation_id: str,
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return _node_id(operation_id, _value_node_kind(index, operation_id, value), value)


def _node_id(operation_id: str, kind: GraphNodeKind, value: str) -> str:
    return _id(kind.value[:5], operation_id, value)


def _value_node_kind(
    index: RunExplorerIndex,
    operation_id: str,
    value: str,
) -> GraphNodeKind:
    operation = index.operations.get(operation_id)
    operation_map = operation if isinstance(operation, dict) else {}
    parameters = operation_map.get("parameters", {})
    parameter_names = {str(name) for name in parameters} if isinstance(parameters, dict) else set()
    normalized = value.removeprefix("input.")
    if value in parameter_names or normalized in parameter_names:
        return GraphNodeKind.PARAMETER
    if value.startswith("input.") and "." not in normalized:
        return GraphNodeKind.PARAMETER
    return GraphNodeKind.PROPERTY


def _graph_sequences(raw: JsonValue) -> list[GraphSequence]:
    if isinstance(raw, list):
        return [
            _sequence_from_path(path, None, "path", None, [])
            for path in raw
            if _string_list(path)
        ]
    if not isinstance(raw, dict):
        return []
    sequences: list[GraphSequence] = []
    for target_operation_id, records in raw.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            sequence_type = str(record.get("type") or "unknown")
            score = _optional_float(record.get("score"))
            parameter_sources = _parameter_sources(record.get("params", {}))
            combined = record.get("combined_sequences", [])
            paths = combined if isinstance(combined, list) else []
            for path in paths:
                if _string_list(path):
                    sequences.append(
                        _sequence_from_path(
                            path,
                            str(target_operation_id),
                            sequence_type,
                            score,
                            parameter_sources,
                        )
                    )
    return sorted(sequences, key=lambda item: (item.target_operation_id or "", item.sequence_type, item.sequence_id))


def _sequence_from_path(
    path: JsonValue,
    target_operation_id: str | None,
    sequence_type: str,
    score: float | None,
    parameter_sources: list[GraphSequenceParameterSource],
) -> GraphSequence:
    operations = [str(item) for item in path] if isinstance(path, list) else []
    return GraphSequence(
        sequence_id=_id("seq", target_operation_id or "", sequence_type, *operations),
        target_operation_id=target_operation_id or (operations[-1] if operations else None),
        sequence_type=sequence_type,
        operations=operations,
        length=len(operations),
        score=score,
        parameter_sources=parameter_sources,
    )


def _parameter_sources(raw: JsonValue) -> list[GraphSequenceParameterSource]:
    if not isinstance(raw, dict):
        return []
    result: list[GraphSequenceParameterSource] = []
    for parameter_name, sources in raw.items():
        if not isinstance(sources, list):
            continue
        for source in sources:
            if not isinstance(source, dict):
                continue
            result.append(
                GraphSequenceParameterSource(
                    parameter_name=str(parameter_name),
                    source_operation_id=_optional_str(source.get("source_endpoint")),
                    source_property_path=_optional_str(source.get("source_param")),
                )
            )
    return result


def _node_filters_from_query(query: GraphNodeQuery) -> _GraphNodeFilters:
    return _GraphNodeFilters(
        node_kind=_optional_enum(GraphNodeKind, query.node_kind, "node_kind"),
        operation_id=query.operation_id,
    )


def _node_filters_from_facets_query(query: GraphFacetsQuery) -> _GraphNodeFilters:
    return _GraphNodeFilters(
        node_kind=_optional_enum(GraphNodeKind, query.node_kind, "node_kind"),
        operation_id=None,
    )


def _edge_filters_from_query(query: GraphEdgeExplorerQuery) -> _GraphEdgeFilters:
    status, all_statuses = _edge_status_filter(query.edge_status)
    return _GraphEdgeFilters(
        edge_status=status,
        include_all_statuses=all_statuses,
        evidence_source=_optional_enum(
            GraphEvidenceSource, query.evidence_source, "evidence_source"
        ),
        from_operation_id=query.from_operation_id,
        to_operation_id=query.to_operation_id,
    )


def _edge_filters_from_facets_query(query: GraphFacetsQuery) -> _GraphEdgeFilters:
    status, all_statuses = _edge_status_filter(query.edge_status)
    return _GraphEdgeFilters(
        edge_status=status,
        include_all_statuses=all_statuses,
        evidence_source=_optional_enum(
            GraphEvidenceSource, query.evidence_source, "evidence_source"
        ),
        from_operation_id=query.from_operation_id,
        to_operation_id=query.to_operation_id,
    )


def _sequence_filters_from_query(query: GraphSequenceQuery) -> _GraphSequenceFilters:
    return _GraphSequenceFilters(
        target_operation_id=query.target_operation_id,
        operation_id=query.operation_id,
        sequence_type=query.sequence_type,
    )


def _sequence_filters_from_facets_query(query: GraphFacetsQuery) -> _GraphSequenceFilters:
    return _GraphSequenceFilters(
        target_operation_id=None,
        operation_id=None,
        sequence_type=query.sequence_type,
    )


def _filter_nodes(nodes: list[GraphNode], filters: _GraphNodeFilters) -> list[GraphNode]:
    return [
        node
        for node in nodes
        if (filters.node_kind is None or node.node_kind == filters.node_kind)
        and (filters.operation_id is None or node.operation_id == filters.operation_id)
    ]


def _filter_edges(
    edges: list[GraphExplorerEdge],
    filters: _GraphEdgeFilters,
) -> list[GraphExplorerEdge]:
    return [
        edge
        for edge in edges
        if (
            filters.include_all_statuses
            or filters.edge_status is None
            or edge.edge_status == filters.edge_status
        )
        and (
            filters.evidence_source is None
            or filters.evidence_source.value in edge.evidence_sources
        )
        and (
            filters.from_operation_id is None
            or edge.from_operation_id == filters.from_operation_id
        )
        and (
            filters.to_operation_id is None
            or edge.to_operation_id == filters.to_operation_id
        )
    ]


def _filter_sequences(
    sequences: list[GraphSequence],
    filters: _GraphSequenceFilters,
) -> list[GraphSequence]:
    return [
        sequence
        for sequence in sequences
        if (
            filters.target_operation_id is None
            or sequence.target_operation_id == filters.target_operation_id
        )
        and (
            filters.operation_id is None
            or filters.operation_id in sequence.operations
        )
        and (
            filters.sequence_type is None
            or sequence.sequence_type == filters.sequence_type
        )
    ]


def _search_nodes(nodes: list[GraphNode], query: str | None) -> list[GraphNode]:
    if not query:
        return nodes
    return query_items(
        nodes,
        spec=DependencyGraphQueryService._node_spec,
        options=QueryOptions(q=query, limit=len(nodes) or 1, offset=0),
    ).items


def _search_edges(edges: list[GraphExplorerEdge], query: str | None) -> list[GraphExplorerEdge]:
    if not query:
        return edges
    return query_items(
        edges,
        spec=DependencyGraphQueryService._edge_spec,
        options=QueryOptions(q=query, limit=len(edges) or 1, offset=0),
    ).items


def _search_sequences(
    sequences: list[GraphSequence],
    query: str | None,
) -> list[GraphSequence]:
    if not query:
        return sequences
    return query_items(
        sequences,
        spec=DependencyGraphQueryService._sequence_spec,
        options=QueryOptions(q=query, limit=len(sequences) or 1, offset=0),
    ).items


def _edge_from_detail(detail: GraphEdgeDetail) -> GraphExplorerEdge:
    return GraphExplorerEdge(
        from_node=detail.from_node,
        to_node=detail.to_node,
        similar_parameters=detail.similar_parameters,
        edge_id=detail.edge_id,
        edge_status=detail.edge_status,
        from_operation_id=detail.from_operation_id,
        to_operation_id=detail.to_operation_id,
        from_node_id=detail.from_node_id,
        to_node_id=detail.to_node_id,
        evidence_count=detail.evidence_count,
        evidence_sources=detail.evidence_sources,
        evidence_preview=detail.evidence_preview,
    )


def _edge_status_filter(value: str | None) -> tuple[GraphEdgeStatus | None, bool]:
    if value is None:
        return GraphEdgeStatus.FINAL, False
    if value == "all":
        return None, True
    return _optional_enum(GraphEdgeStatus, value, "edge_status"), False


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


def _read_optional_json(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
    artifact_id: str,
) -> JsonValue:
    try:
        return repository.read_json_artifact(run_name, artifact_id)
    except ArtifactNotFound:
        return None


def _evidence_preview(evidence: GraphEvidence) -> str:
    left = evidence.value1 or ""
    right = evidence.value2 or ""
    relation = evidence.relation_hint or evidence.source.value
    return f"{left} -> {right} ({relation})"


def _facet(records: list, accessor) -> list[ConstraintFacetBucket]:
    counts = Counter(value for record in records if (value := accessor(record)))
    return [
        ConstraintFacetBucket(key=str(key), count=count)
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _evidence_source_facet(edges: list[GraphExplorerEdge]) -> list[ConstraintFacetBucket]:
    counts = Counter(source for edge in edges for source in edge.evidence_sources)
    return [
        ConstraintFacetBucket(key=str(key), count=count)
        for key, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _id(prefix: str, *parts: str) -> str:
    raw = "\x1f".join(parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _optional_str(value: JsonValue) -> str | None:
    return None if value is None else str(value)


def _optional_float(value: JsonValue) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _string_list(value: JsonValue) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
