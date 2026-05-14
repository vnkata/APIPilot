from __future__ import annotations

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    GroupCountResponse,
    PaginationMetadata,
)
from api_testing.backend.domain.models import (
    DependencyGraph,
    GraphEdge,
    GraphSimilarity,
    GroupedPage,
)


class GraphSimilarityResponse(BackendBaseModel):
    value1: str | None = None
    value2: str | None = None
    in_value: str | None = None

    @classmethod
    def from_domain(cls, similarity: GraphSimilarity) -> "GraphSimilarityResponse":
        return cls(
            value1=similarity.value1,
            value2=similarity.value2,
            in_value=similarity.in_value,
        )


class GraphEdgeResponse(BackendBaseModel):
    from_node: str
    to_node: str
    similar_parameters: list[GraphSimilarityResponse]

    @classmethod
    def from_domain(cls, edge: GraphEdge) -> "GraphEdgeResponse":
        return cls(
            from_node=edge.from_node,
            to_node=edge.to_node,
            similar_parameters=[
                GraphSimilarityResponse.from_domain(similarity)
                for similarity in edge.similar_parameters
            ],
        )


class GraphEdgePageResponse(BackendBaseModel):
    run_name: str
    items: list[GraphEdgeResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: GroupedPage[GraphEdge],
    ) -> "GraphEdgePageResponse":
        return cls(
            run_name=run_name,
            items=[GraphEdgeResponse.from_domain(edge) for edge in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class DependencyGraphResponse(BackendBaseModel):
    run_name: str
    nodes: list[str]
    edges: list[GraphEdgeResponse]

    @classmethod
    def from_domain(cls, graph: DependencyGraph) -> "DependencyGraphResponse":
        return cls(
            run_name=graph.run_name,
            nodes=graph.nodes,
            edges=[GraphEdgeResponse.from_domain(edge) for edge in graph.edges],
        )
