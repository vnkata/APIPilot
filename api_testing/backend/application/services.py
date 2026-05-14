"""Thin compatibility facade for APIPilot artifact read services."""

from __future__ import annotations

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    ConstraintEntryQuery,
    GraphEdgeQuery,
    HarEntryQuery,
    InvariantQuery,
    MAX_PAGE_LIMIT,
    ReportEntryQuery,
    TestCaseQuery,
)
from api_testing.backend.application.read_services.artifacts import (
    ArtifactCatalogService,
    ArtifactContentService,
)
from api_testing.backend.application.read_services.constraints import (
    DynamicConstraintQueryService,
    StaticConstraintQueryService,
)
from api_testing.backend.application.read_services.graphs import (
    DependencyGraphQueryService,
)
from api_testing.backend.application.read_services.history import HistoryQueryService
from api_testing.backend.application.read_services.operations import OperationQueryService
from api_testing.backend.application.read_services.reports import ReportQueryService
from api_testing.backend.application.read_services.runs import RunQueryService
from api_testing.backend.application.read_services.test_cases import TestCaseQueryService
from api_testing.backend.domain.models import (
    ArtifactContent,
    ArtifactMetadata,
    DependencyGraph,
    DynamicConstraints,
    GraphEdge,
    GroupedPage,
    HarEntry,
    HarSession,
    InvariantDetail,
    OperationDetail,
    OperationSummary,
    Page,
    Reports,
    Run,
    RunSummary,
    StaticConstraints,
    StatusReportEntry,
    TestCase,
    ConstraintEntryDetail,
)


class ArtifactQueryService:
    """Compatibility facade that delegates each read capability to focused services."""

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        artifact_catalog_service = ArtifactCatalogService(repository)
        artifact_content_service = ArtifactContentService(repository)
        operation_service = OperationQueryService(repository)
        report_service = ReportQueryService(repository)
        graph_service = DependencyGraphQueryService(repository)
        static_constraint_service = StaticConstraintQueryService(repository)
        dynamic_constraint_service = DynamicConstraintQueryService(repository)
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
        query: GraphEdgeQuery,
    ) -> GroupedPage[GraphEdge]:
        return self.graph.list_graph_edges(run_name, query)

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
