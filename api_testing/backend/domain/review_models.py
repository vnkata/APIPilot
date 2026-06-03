from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import JsonValue


@dataclass(frozen=True, slots=True)
class CombinationReview:
    run_name: str
    combination_id: str
    review_key: str
    review_state: str
    decision_source: str | None
    manual_decision: str | None
    rationale: str | None
    custom_final_constraint: str | None
    runtime_recommendation: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CounterExampleCase:
    case_id: str
    review_key: str
    case_state: str
    request: JsonValue
    request_display: JsonValue | None
    source: str
    rationale: str | None
    generation_id: str | None
    target_truth_vector: JsonValue | None
    risk: str | None
    expected_observation: str | None
    validation_error: JsonValue | None
    planner_version: str | None
    source_metadata: JsonValue | None
    runtime_verdict: str | None
    runtime_result: JsonValue | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CombinationReviewEvent:
    event_id: str
    review_key: str
    sequence: int
    event_type: str
    metadata: JsonValue
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CombinationReviewDetail:
    review: CombinationReview
    cases: list[CounterExampleCase]
    events: list[CombinationReviewEvent]
    target_base_url_suggestions: list[str]
