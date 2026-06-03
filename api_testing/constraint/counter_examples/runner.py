"""Approved counter-example execution boundary."""

from __future__ import annotations

from typing import Any, Protocol

from .models import ApprovedCounterExampleCase, CounterExampleExecutionResult


class CounterExampleExecutor(Protocol):
    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute an approved request and return sanitized runtime evidence."""


def run_approved_cases(
    cases: list[ApprovedCounterExampleCase],
    executor: CounterExampleExecutor,
) -> list[CounterExampleExecutionResult]:
    results: list[CounterExampleExecutionResult] = []
    for case in cases:
        evidence = executor.execute(case.request)
        results.append(
            CounterExampleExecutionResult(
                case_id=case.case_id,
                runtime_verdict=str(evidence.get("runtime_verdict") or "INCONCLUSIVE_EVALUATION"),
                runtime_result=dict(evidence.get("runtime_result") or evidence),
            )
        )
    return results
