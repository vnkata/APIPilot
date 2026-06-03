"""Draft-only counter-example generation boundary."""

from __future__ import annotations

from typing import Any, Mapping, Protocol
from uuid import uuid4

from pydantic import ValidationError

from .models import CounterExampleDraftCase, CounterExamplePlannerCase


class CounterExampleDraftProvider(Protocol):
    def generate(self, context: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Return draft case payloads for a review context."""


def generate_draft_cases(
    context: Mapping[str, Any],
    provider: CounterExampleDraftProvider,
) -> list[CounterExampleDraftCase]:
    cases: list[CounterExampleDraftCase] = []
    for raw_case in provider.generate(context):
        request = raw_case.get("request")
        if not isinstance(request, dict):
            continue
        planner_keys = {"target_truth_vector", "risk", "expected_observation"}
        if planner_keys & set(raw_case):
            try:
                planned = CounterExamplePlannerCase.model_validate(raw_case)
            except ValidationError:
                continue
            cases.append(
                CounterExampleDraftCase(
                    case_id=str(planned.case_id or f"ce_{uuid4().hex}"),
                    request=planned.request.model_dump(exclude_none=True),
                    target_truth_vector=planned.target_truth_vector.model_dump(),
                    rationale=planned.rationale,
                    risk=planned.risk,
                    expected_observation=planned.expected_observation,
                    source=str(raw_case.get("source") or "llm_draft"),
                )
            )
            continue
        cases.append(
            CounterExampleDraftCase(
                case_id=str(raw_case.get("case_id") or f"ce_{uuid4().hex}"),
                request=request,
                rationale=(
                    str(raw_case["rationale"])
                    if raw_case.get("rationale") is not None
                    else None
                ),
                source=str(raw_case.get("source") or "llm_draft"),
            )
        )
    return cases
