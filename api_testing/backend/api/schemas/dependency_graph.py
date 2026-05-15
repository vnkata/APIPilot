from __future__ import annotations

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    GroupCountResponse,
    PaginationMetadata,
)
from api_testing.backend.domain.models import (
    ConstraintFacetBucket,
    DependencyGraph,
    GraphEdge,
    GraphEdgeDetail,
    GraphEvidence,
    GraphExplorerEdge,
    GraphFacets,
    GraphNode,
    GraphSequence,
    GraphSequenceParameterSource,
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
    items: list["GraphExplorerEdgeResponse"]
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
            items=[GraphExplorerEdgeResponse.from_domain(edge) for edge in page.items],
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


class GraphNodeResponse(BackendBaseModel):
    node_id: str
    node_kind: str
    operation_id: str
    label: str
    property_path: str | None = None
    parameter_name: str | None = None
    http_method: str | None = None
    path_template: str | None = None
    in_degree: int
    out_degree: int

    @classmethod
    def from_domain(cls, node: GraphNode) -> "GraphNodeResponse":
        return cls(
            node_id=node.node_id,
            node_kind=node.node_kind.value,
            operation_id=node.operation_id,
            label=node.label,
            property_path=node.property_path,
            parameter_name=node.parameter_name,
            http_method=node.http_method.value if node.http_method else None,
            path_template=node.path_template,
            in_degree=node.in_degree,
            out_degree=node.out_degree,
        )


class GraphNodePageResponse(BackendBaseModel):
    run_name: str
    items: list[GraphNodeResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: GroupedPage[GraphNode],
    ) -> "GraphNodePageResponse":
        return cls(
            run_name=run_name,
            items=[GraphNodeResponse.from_domain(node) for node in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class GraphExplorerEdgeResponse(GraphEdgeResponse):
    edge_id: str
    edge_status: str
    from_operation_id: str
    to_operation_id: str
    from_node_id: str
    to_node_id: str
    evidence_count: int
    evidence_sources: list[str]
    evidence_preview: list[str]

    @classmethod
    def from_domain(cls, edge: GraphExplorerEdge) -> "GraphExplorerEdgeResponse":
        return cls(
            from_node=edge.from_node,
            to_node=edge.to_node,
            similar_parameters=[
                GraphSimilarityResponse.from_domain(similarity)
                for similarity in edge.similar_parameters
            ],
            edge_id=edge.edge_id,
            edge_status=edge.edge_status.value,
            from_operation_id=edge.from_operation_id,
            to_operation_id=edge.to_operation_id,
            from_node_id=edge.from_node_id,
            to_node_id=edge.to_node_id,
            evidence_count=edge.evidence_count,
            evidence_sources=edge.evidence_sources,
            evidence_preview=edge.evidence_preview,
        )


class GraphEvidenceResponse(BackendBaseModel):
    evidence_id: str
    source: str
    source_artifact_id: str
    value1: str | None = None
    value2: str | None = None
    relation_hint: str | None = None
    from_evidence_node_id: str | None = None
    to_evidence_node_id: str | None = None

    @classmethod
    def from_domain(cls, evidence: GraphEvidence) -> "GraphEvidenceResponse":
        return cls(
            evidence_id=evidence.evidence_id,
            source=evidence.source.value,
            source_artifact_id=evidence.source_artifact_id,
            value1=evidence.value1,
            value2=evidence.value2,
            relation_hint=evidence.relation_hint,
            from_evidence_node_id=evidence.from_evidence_node_id,
            to_evidence_node_id=evidence.to_evidence_node_id,
        )


class GraphEdgeDetailResponse(GraphExplorerEdgeResponse):
    evidence: list[GraphEvidenceResponse]

    @classmethod
    def from_domain(cls, edge: GraphEdgeDetail) -> "GraphEdgeDetailResponse":
        base = GraphExplorerEdgeResponse.from_domain(edge).model_dump()
        return cls(
            **base,
            evidence=[GraphEvidenceResponse.from_domain(item) for item in edge.evidence],
        )


class GraphSequenceParameterSourceResponse(BackendBaseModel):
    parameter_name: str
    source_operation_id: str | None = None
    source_property_path: str | None = None

    @classmethod
    def from_domain(
        cls, source: GraphSequenceParameterSource
    ) -> "GraphSequenceParameterSourceResponse":
        return cls(
            parameter_name=source.parameter_name,
            source_operation_id=source.source_operation_id,
            source_property_path=source.source_property_path,
        )


class GraphSequenceResponse(BackendBaseModel):
    sequence_id: str
    target_operation_id: str | None = None
    sequence_type: str
    operations: list[str]
    length: int
    score: float | None = None
    parameter_sources: list[GraphSequenceParameterSourceResponse]

    @classmethod
    def from_domain(cls, sequence: GraphSequence) -> "GraphSequenceResponse":
        return cls(
            sequence_id=sequence.sequence_id,
            target_operation_id=sequence.target_operation_id,
            sequence_type=sequence.sequence_type,
            operations=sequence.operations,
            length=sequence.length,
            score=sequence.score,
            parameter_sources=[
                GraphSequenceParameterSourceResponse.from_domain(item)
                for item in sequence.parameter_sources
            ],
        )


class GraphSequencePageResponse(BackendBaseModel):
    run_name: str
    items: list[GraphSequenceResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: GroupedPage[GraphSequence],
    ) -> "GraphSequencePageResponse":
        return cls(
            run_name=run_name,
            items=[GraphSequenceResponse.from_domain(item) for item in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class GraphFacetBucketResponse(BackendBaseModel):
    key: str
    count: int

    @classmethod
    def from_domain(cls, bucket: ConstraintFacetBucket) -> "GraphFacetBucketResponse":
        return cls(key=bucket.key, count=bucket.count)


class GraphFacetsResponse(BackendBaseModel):
    edge_status: list[GraphFacetBucketResponse]
    evidence_source: list[GraphFacetBucketResponse]
    from_operation_id: list[GraphFacetBucketResponse]
    to_operation_id: list[GraphFacetBucketResponse]
    node_kind: list[GraphFacetBucketResponse]
    sequence_type: list[GraphFacetBucketResponse]

    @classmethod
    def from_domain(cls, facets: GraphFacets) -> "GraphFacetsResponse":
        return cls(
            edge_status=[
                GraphFacetBucketResponse.from_domain(bucket)
                for bucket in facets.edge_status
            ],
            evidence_source=[
                GraphFacetBucketResponse.from_domain(bucket)
                for bucket in facets.evidence_source
            ],
            from_operation_id=[
                GraphFacetBucketResponse.from_domain(bucket)
                for bucket in facets.from_operation_id
            ],
            to_operation_id=[
                GraphFacetBucketResponse.from_domain(bucket)
                for bucket in facets.to_operation_id
            ],
            node_kind=[
                GraphFacetBucketResponse.from_domain(bucket)
                for bucket in facets.node_kind
            ],
            sequence_type=[
                GraphFacetBucketResponse.from_domain(bucket)
                for bucket in facets.sequence_type
            ],
        )
