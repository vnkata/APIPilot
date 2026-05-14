"""Dependency graph read services."""

from __future__ import annotations

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    GraphEdgeQuery,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.utils import graph_similarities
from api_testing.backend.domain.models import DependencyGraph, GraphEdge, GroupedPage


class DependencyGraphQueryService:
    """Builds aggregate and detailed dependency graph read models."""

    _edge_spec = QuerySpec[GraphEdge](
        sort_fields={
            "from_node": lambda item: item.from_node,
            "to_node": lambda item: item.to_node,
        },
        group_fields={
            "from_node": lambda item: item.from_node,
            "to_node": lambda item: item.to_node,
        },
        search_fields=[
            lambda item: item.from_node,
            lambda item: item.to_node,
        ],
        default_sort=("from_node", "to_node"),
    )

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def get_dependency_graph(self, run_name: str) -> DependencyGraph:
        raw = self.repository.read_json_artifact(
            run_name, "semantic_property_dependency_graph"
        )
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

    def list_graph_edges(
        self,
        run_name: str,
        query: GraphEdgeQuery,
    ) -> GroupedPage[GraphEdge]:
        records = [
            edge
            for edge in self.get_dependency_graph(run_name).edges
            if (query.from_node is None or edge.from_node == query.from_node)
            and (query.to_node is None or edge.to_node == query.to_node)
        ]
        return query_items(records, spec=self._edge_spec, options=query.options)
