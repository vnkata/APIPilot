"""Core counter-example review models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TruthValue = Literal["true", "false", "unknown"]
RiskLevel = Literal["low", "medium", "high"]


class CounterExampleTargetTruthVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    static_constraint: TruthValue
    dynamic_constraint: TruthValue


class CounterExampleRequestDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = Field(description="HTTP method for the diagnostic request.")
    path: str = Field(description="Endpoint path template or concrete safe path.")
    path_parameters: dict[str, Any] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    body: Any | None = None


class CounterExamplePlannerCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str | None = None
    request: CounterExampleRequestDraft
    target_truth_vector: CounterExampleTargetTruthVector
    rationale: str
    risk: RiskLevel
    expected_observation: str


class CounterExamplePlannerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[CounterExamplePlannerCase]


@dataclass(frozen=True, slots=True)
class CounterExampleDraftCase:
    case_id: str
    request: dict[str, Any]
    target_truth_vector: dict[str, str] = field(
        default_factory=lambda: {
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        }
    )
    rationale: str | None = None
    risk: str | None = None
    expected_observation: str | None = None
    validation_error: dict[str, Any] | None = None
    source: str = "draft"


@dataclass(frozen=True, slots=True)
class ApprovedCounterExampleCase:
    case_id: str
    request: dict[str, Any]
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class CounterExampleExecutionResult:
    case_id: str
    runtime_verdict: str
    runtime_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    manual_decision: str
    rationale: str
    custom_final_constraint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
