"""Run catalog and summary read services."""

from __future__ import annotations

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.read_services.constraints import (
    DynamicConstraintQueryService,
    StaticConstraintQueryService,
)
from api_testing.backend.application.read_services.history import HistoryQueryService
from api_testing.backend.application.read_services.operations import OperationQueryService
from api_testing.backend.application.read_services.reports import ReportQueryService
from api_testing.backend.application.read_services.test_cases import TestCaseQueryService
from api_testing.backend.domain.models import ArtifactAvailability, Run, RunSummary


class RunQueryService:
    """Builds run catalog and summary read models."""

    def __init__(
        self,
        repository: ArtifactRepositoryProtocol,
        *,
        operation_service: OperationQueryService,
        report_service: ReportQueryService,
        static_constraint_service: StaticConstraintQueryService,
        dynamic_constraint_service: DynamicConstraintQueryService,
        test_case_service: TestCaseQueryService,
        history_service: HistoryQueryService,
    ) -> None:
        self.repository = repository
        self.operation_service = operation_service
        self.report_service = report_service
        self.static_constraint_service = static_constraint_service
        self.dynamic_constraint_service = dynamic_constraint_service
        self.test_case_service = test_case_service
        self.history_service = history_service

    def list_runs(self) -> list[Run]:
        return self.repository.list_runs()

    def get_run(self, run_name: str) -> Run:
        return self.repository.get_run(run_name)

    def get_run_summary(self, run_name: str) -> RunSummary:
        run = self.repository.get_run(run_name)
        availability = self.availability(run_name)
        operations = (
            self.operation_service.list_operations(run_name)
            if availability.specification
            else []
        )
        har_sessions = (
            self.history_service.list_har_sessions(run_name)
            if availability.history
            else []
        )
        static_constraints = (
            self.static_constraint_service.get_static_constraints(run_name)
            if availability.static_constraints
            else None
        )
        dynamic_constraints = (
            self.dynamic_constraint_service.get_dynamic_constraints(run_name)
            if availability.dynamic_constraints
            else None
        )
        reports = self.report_service.get_reports(run_name) if availability.reports else None
        return RunSummary(
            run_name=run.run_name,
            artifact_count=run.artifact_count,
            operation_count=len(operations),
            test_case_count=self.test_case_service.count_test_cases(run_name)
            if availability.test_cases
            else 0,
            har_session_count=len(har_sessions),
            static_constraint_count=static_constraints.constraint_count
            if static_constraints
            else 0,
            dynamic_constraint_count=dynamic_constraints.constraint_count
            if dynamic_constraints
            else 0,
            report_status_counts=reports.status_counts if reports else {},
            available_artifacts=availability,
        )

    def availability(self, run_name: str) -> ArtifactAvailability:
        artifacts = {
            artifact.artifact_id for artifact in self.repository.list_artifacts(run_name)
        }
        return ArtifactAvailability(
            specification="specification" in artifacts,
            reports="reports" in artifacts,
            graph="semantic_property_dependency_graph" in artifacts,
            static_constraints="static_constraint_miner" in artifacts,
            dynamic_constraints="dynamic_constraint_miner" in artifacts,
            test_cases="test_cases_json" in artifacts,
            invariants="invariants_csv" in artifacts,
            history=any(artifact_id.startswith("history_") for artifact_id in artifacts),
        )
