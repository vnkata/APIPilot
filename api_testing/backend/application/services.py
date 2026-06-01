"""Thin compatibility facade for APIPilot artifact read services."""

from __future__ import annotations

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    CombinationFacetsQuery,
    CombinationQuery,
    ConstraintEntryQuery,
    ConstraintExplorerQuery,
    ConstraintFacetsQuery,
    GraphEdgeExplorerQuery,
    GraphEdgeQuery,
    GraphFacetsQuery,
    GraphNodeQuery,
    GraphSequenceQuery,
    HarEntryQuery,
    InvariantExplorerQuery,
    InvariantFacetsQuery,
    InvariantQuery,
    MAX_PAGE_LIMIT,
    OperationExplorerQuery,
    OperationFacetsQuery,
    ReportEntryQuery,
    TestCaseQuery,
)
from api_testing.backend.application.read_services.constraint_explorer import (
    ConstraintExplorerService,
)
from api_testing.backend.application.read_services.constraint_combination import (
    ConstraintCombinationService,
)
from api_testing.backend.application.read_services.artifacts import (
    ArtifactCatalogService,
    ArtifactContentService,
)
from api_testing.backend.application.read_services.constraints import (
    DynamicConstraintQueryService,
    StaticConstraintQueryService,
)
from api_testing.backend.application.read_services.explorer_index import (
    RunExplorerIndexService,
)
from api_testing.backend.application.read_services.graphs import (
    DependencyGraphQueryService,
)
from api_testing.backend.application.read_services.history import HistoryQueryService
from api_testing.backend.application.read_services.invariant_explorer import (
    InvariantExplorerService,
)
from api_testing.backend.application.read_services.operations import OperationQueryService
from api_testing.backend.application.read_services.reports import ReportQueryService
from api_testing.backend.application.read_services.runs import RunQueryService
from api_testing.backend.application.read_services.test_cases import TestCaseQueryService
from api_testing.backend.domain.models import (
    ArtifactContent,
    ArtifactMetadata,
    CombinationDetail,
    CombinationEntryPage,
    CombinationFacets,
    CombinationSummary,
    DependencyGraph,
    DynamicConstraints,
    GraphEdge,
    GraphEdgeDetail,
    GraphExplorerEdge,
    GraphFacets,
    GraphNode,
    GraphSequence,
    GroupedPage,
    HarEntry,
    HarSession,
    InvariantDetail,
    InvariantExplorerDetail,
    InvariantExplorerFacets,
    InvariantExplorerPage,
    OperationDetail,
    OperationExplorerDetail,
    OperationExplorerPage,
    OperationFacets,
    OperationSummary,
    Page,
    Reports,
    Run,
    RunSummary,
    StaticConstraints,
    StatusReportEntry,
    TestCase,
    ConstraintEntryDetail,
    ConstraintExplorerDetail,
    ConstraintExplorerPage,
    ConstraintFacets,
)


class ArtifactQueryService:
    """Compatibility facade that delegates each read capability to focused services."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        artifact_catalog_service = ArtifactCatalogService(repository)
        artifact_content_service = ArtifactContentService(repository)
        report_service = ReportQueryService(repository)
        static_constraint_service = StaticConstraintQueryService(repository)
        dynamic_constraint_service = DynamicConstraintQueryService(repository)
        constraint_explorer_service = ConstraintExplorerService(repository)
        combination_service = ConstraintCombinationService(repository)
        explorer_index_service = RunExplorerIndexService(
            repository,
            constraint_explorer_service,
        )
        operation_service = OperationQueryService(repository, explorer_index_service)
        invariant_explorer_service = InvariantExplorerService(
            repository,
            explorer_index_service,
        )
        graph_service = DependencyGraphQueryService(repository, explorer_index_service)
        operation_service.configure_explorer_dependencies(
            invariant_explorer=invariant_explorer_service,
            graph_service=graph_service,
        )
        test_case_service = TestCaseQueryService(repository)
        history_service = HistoryQueryService(repository)
        run_service = RunQueryService(
            repository,
            operation_service=operation_service,
            report_service=report_service,
            static_constraint_service=static_constraint_service,
            dynamic_constraint_service=dynamic_constraint_service,
            test_case_service=test_case_service,
            history_service=history_service,
        )

        self.runs = run_service
        self.artifacts = artifact_catalog_service
        self.artifact_content = artifact_content_service
        self.operations = operation_service
        self.reports = report_service
        self.graph = graph_service
        self.static_constraints = static_constraint_service
        self.dynamic_constraints = dynamic_constraint_service
        self.constraint_explorer = constraint_explorer_service
        self.combination = combination_service
        self.invariant_explorer = invariant_explorer_service
        self.test_cases = test_case_service
        self.history = history_service

    def list_runs(self) -> list[Run]:
        return self.runs.list_runs()

    def get_run(self, run_name: str) -> Run:
        return self.runs.get_run(run_name)

    def get_run_summary(self, run_name: str) -> RunSummary:
        return self.runs.get_run_summary(run_name)

    def list_artifacts(self, run_name: str) -> list[ArtifactMetadata]:
        return self.artifacts.list_artifacts(run_name)

    def get_artifact_content(
        self,
        run_name: str,
        *,
        artifact_id: str,
        raw: bool,
    ) -> ArtifactContent:
        return self.artifact_content.get_artifact_content(
            run_name,
            artifact_id=artifact_id,
            raw=raw,
        )

    def list_operations(self, run_name: str) -> list[OperationSummary]:
        return self.operations.list_operations(run_name)

    def get_operation(self, run_name: str, operation_id: str) -> OperationDetail:
        return self.operations.get_operation(run_name, operation_id)

    def list_operation_explorer_entries(
        self,
        run_name: str,
        query: OperationExplorerQuery,
    ) -> OperationExplorerPage:
        return self.operations.list_explorer_entries(run_name, query)

    def get_operation_explorer_entry(
        self,
        run_name: str,
        operation_key: str,
    ) -> OperationExplorerDetail:
        return self.operations.get_explorer_entry(run_name, operation_key)

    def get_operation_explorer_facets(
        self,
        run_name: str,
        query: OperationFacetsQuery,
    ) -> OperationFacets:
        return self.operations.get_explorer_facets(run_name, query)

    def get_reports(self, run_name: str) -> Reports:
        return self.reports.get_reports(run_name)

    def list_report_entries(
        self,
        run_name: str,
        query: ReportEntryQuery,
    ) -> GroupedPage[StatusReportEntry]:
        return self.reports.list_report_entries(run_name, query)

    def get_dependency_graph(self, run_name: str) -> DependencyGraph:
        return self.graph.get_dependency_graph(run_name)

    def list_graph_edges(
        self,
        run_name: str,
        query: GraphEdgeQuery | GraphEdgeExplorerQuery,
    ) -> GroupedPage[GraphExplorerEdge]:
        return self.graph.list_graph_edges(run_name, query)

    def get_graph_edge(self, run_name: str, edge_id: str) -> GraphEdgeDetail:
        return self.graph.get_graph_edge(run_name, edge_id)

    def list_graph_nodes(
        self,
        run_name: str,
        query: GraphNodeQuery,
    ) -> GroupedPage[GraphNode]:
        return self.graph.list_graph_nodes(run_name, query)

    def list_graph_sequences(
        self,
        run_name: str,
        query: GraphSequenceQuery,
    ) -> GroupedPage[GraphSequence]:
        return self.graph.list_graph_sequences(run_name, query)

    def get_graph_sequence(self, run_name: str, sequence_id: str) -> GraphSequence:
        return self.graph.get_graph_sequence(run_name, sequence_id)

    def get_graph_facets(
        self,
        run_name: str,
        query: GraphFacetsQuery,
    ) -> GraphFacets:
        return self.graph.get_graph_facets(run_name, query)

    def get_static_constraints(self, run_name: str) -> StaticConstraints:
        return self.static_constraints.get_static_constraints(run_name)

    def list_static_constraint_entries(
        self,
        run_name: str,
        query: ConstraintEntryQuery,
    ) -> GroupedPage[ConstraintEntryDetail]:
        return self.static_constraints.list_static_constraint_entries(run_name, query)

    def get_dynamic_constraints(self, run_name: str) -> DynamicConstraints:
        return self.dynamic_constraints.get_dynamic_constraints(run_name)

    def list_dynamic_constraint_entries(
        self,
        run_name: str,
        query: ConstraintEntryQuery,
    ) -> GroupedPage[ConstraintEntryDetail]:
        return self.dynamic_constraints.list_dynamic_constraint_entries(run_name, query)

    def list_constraint_explorer_entries(
        self,
        run_name: str,
        query: ConstraintExplorerQuery,
    ) -> ConstraintExplorerPage:
        return self.constraint_explorer.list_entries(run_name, query)

    def get_constraint_explorer_entry(
        self,
        run_name: str,
        constraint_id: str,
    ) -> ConstraintExplorerDetail:
        return self.constraint_explorer.get_entry(run_name, constraint_id)

    def get_constraint_explorer_facets(
        self,
        run_name: str,
        query: ConstraintFacetsQuery,
    ) -> ConstraintFacets:
        return self.constraint_explorer.get_facets(run_name, query)

    def get_combination_summary(self, run_name: str) -> CombinationSummary:
        return self.combination.get_summary(run_name)

    def list_combination_entries(
        self,
        run_name: str,
        query: CombinationQuery,
    ) -> CombinationEntryPage:
        return self.combination.list_entries(run_name, query)

    def get_combination_entry(
        self,
        run_name: str,
        combination_id: str,
    ) -> CombinationDetail:
        return self.combination.get_entry(run_name, combination_id)

    def get_combination_facets(
        self,
        run_name: str,
        query: CombinationFacetsQuery,
    ) -> CombinationFacets:
        return self.combination.get_facets(run_name, query)

    def list_invariant_explorer_entries(
        self,
        run_name: str,
        query: InvariantExplorerQuery,
    ) -> InvariantExplorerPage:
        return self.invariant_explorer.list_entries(run_name, query)

    def get_invariant_explorer_entry(
        self,
        run_name: str,
        invariant_id: str,
    ) -> InvariantExplorerDetail:
        return self.invariant_explorer.get_entry(run_name, invariant_id)

    def get_invariant_explorer_facets(
        self,
        run_name: str,
        query: InvariantFacetsQuery,
    ) -> InvariantExplorerFacets:
        return self.invariant_explorer.get_facets(run_name, query)

    def list_invariants(
        self,
        run_name: str,
        query: InvariantQuery,
    ) -> GroupedPage[InvariantDetail]:
        return self.dynamic_constraints.list_invariants(run_name, query)

    def list_test_cases(
        self,
        run_name: str,
        *,
        operation_id: str | None,
        status_code: int | None,
        limit: int,
        offset: int,
        include_body: bool,
    ) -> Page[TestCase]:
        return self.test_cases.list_test_cases(
            run_name,
            TestCaseQuery(
                operation_id=operation_id,
                status_code=status_code,
                limit=limit,
                offset=offset,
                include_body=include_body,
            ),
        )

    def list_har_sessions(self, run_name: str) -> list[HarSession]:
        return self.history.list_har_sessions(run_name)

    def list_har_entries(
        self,
        run_name: str,
        *,
        session_id: str,
        limit: int,
        offset: int,
        include_body: bool,
    ) -> Page[HarEntry]:
        return self.history.list_har_entries(
            run_name,
            HarEntryQuery(
                session_id=session_id,
                limit=limit,
                offset=offset,
                include_body=include_body,
            ),
        )
