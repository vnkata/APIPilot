from __future__ import annotations

from datetime import datetime

from pydantic import Field

from api_testing.backend.api.schemas.common import BackendBaseModel
from api_testing.backend.domain.models import (
    ArtifactAvailability,
    Run,
    RunSummary,
)


class ArtifactAvailabilityResponse(BackendBaseModel):
    specification: bool = False
    reports: bool = False
    graph: bool = False
    static_constraints: bool = False
    dynamic_constraints: bool = False
    test_cases: bool = False
    invariants: bool = False
    history: bool = False

    @classmethod
    def from_domain(
        cls, availability: ArtifactAvailability
    ) -> "ArtifactAvailabilityResponse":
        return cls(
            specification=availability.specification,
            reports=availability.reports,
            graph=availability.graph,
            static_constraints=availability.static_constraints,
            dynamic_constraints=availability.dynamic_constraints,
            test_cases=availability.test_cases,
            invariants=availability.invariants,
            history=availability.history,
        )


class RunMetadataResponse(BackendBaseModel):
    run_name: str
    artifact_count: int = Field(ge=0)
    has_history: bool
    size_bytes: int = Field(ge=0)
    modified_at: datetime | None = None

    @classmethod
    def from_domain(cls, run: Run) -> "RunMetadataResponse":
        return cls(
            run_name=run.run_name,
            artifact_count=run.artifact_count,
            has_history=run.has_history,
            size_bytes=run.size_bytes,
            modified_at=run.modified_at,
        )


class RunCatalogResponse(BackendBaseModel):
    runs: list[RunMetadataResponse]

    @classmethod
    def from_domain(cls, runs: list[Run]) -> "RunCatalogResponse":
        return cls(runs=[RunMetadataResponse.from_domain(run) for run in runs])


class RunSummaryResponse(BackendBaseModel):
    run_name: str
    artifact_count: int = Field(ge=0)
    operation_count: int = Field(ge=0)
    test_case_count: int = Field(ge=0)
    har_session_count: int = Field(ge=0)
    static_constraint_count: int = Field(ge=0)
    dynamic_constraint_count: int = Field(ge=0)
    report_status_counts: dict[str, int]
    available_artifacts: ArtifactAvailabilityResponse

    @classmethod
    def from_domain(cls, summary: RunSummary) -> "RunSummaryResponse":
        return cls(
            run_name=summary.run_name,
            artifact_count=summary.artifact_count,
            operation_count=summary.operation_count,
            test_case_count=summary.test_case_count,
            har_session_count=summary.har_session_count,
            static_constraint_count=summary.static_constraint_count,
            dynamic_constraint_count=summary.dynamic_constraint_count,
            report_status_counts=summary.report_status_counts,
            available_artifacts=ArtifactAvailabilityResponse.from_domain(
                summary.available_artifacts
            ),
        )
